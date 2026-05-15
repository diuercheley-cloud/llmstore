from __future__ import annotations

import csv
import html
import io
import json
import logging
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.services.routing.commercial_cluster_registry import validate_tenant_scope
from app.services.routing.commercial_federation import summarize_federated_overview
from app.services.routing.commercial_report_export import sanitize_report_payload

logger = logging.getLogger(__name__)


def score_cluster(
    cluster_data: dict[str, Any],
    *,
    region_preference: str | None = None,
    settings: Settings | None = None,
    qos_tier: Any | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    
    # Weights from settings
    w_margin = cfg.commercial_global_routing_margin_weight
    w_latency = cfg.commercial_global_routing_latency_weight
    w_health = cfg.commercial_global_routing_health_weight
    w_region = cfg.commercial_global_routing_region_weight
    w_priority = cfg.commercial_global_routing_priority_weight

    reasons = []
    warnings = []

    # Phase 20: QoS Tier Enforcement
    if qos_tier:
        # Cross-cluster check
        if not qos_tier.allow_cross_cluster:
            warnings.append(f"QoS Tier {qos_tier.name} forbids cross-cluster routing")
            # We don't reject yet, just penalty or let rank_clusters handle it
        
        # Degraded check
        if cluster_data.get("status") == "degraded" and not qos_tier.allow_degraded_cluster:
            warnings.append(f"QoS Tier {qos_tier.name} forbids degraded clusters")
    
    # 1. Health Score (0-100)
    status = cluster_data.get("status", "offline")
    if status == "active":
        health_val = 100
    elif status == "degraded":
        health_val = 50
        warnings.append(f"Cluster {cluster_data['cluster_id']} is degraded")
    else:
        health_val = 0
        warnings.append(f"Cluster {cluster_data['cluster_id']} is {status}")
        
    # 2. Margin Score (0-100)
    # actual_margin_brl vs actual_revenue_brl
    actual_margin = float(cluster_data.get("actual_margin_brl", 0))
    actual_revenue = float(cluster_data.get("actual_revenue_brl", 0))
    
    if actual_revenue > 0:
        margin_pct = (actual_margin / actual_revenue) * 100
    else:
        # If no data, use a neutral/conservative value or default to high if local
        margin_pct = 20.0 
        
    # Normalize margin_pct to 0-100 scale (assuming 50% is max desirable)
    margin_val = min(max(margin_pct * 2, 0), 100)
    if actual_margin < 0:
        margin_val = 0
        warnings.append("Negative margin detected")

    # 3. Latency Score (0-100)
    avg_latency = float(cluster_data.get("avg_latency_ms", 0))
    max_latency = float(cfg.commercial_global_routing_max_latency_ms)
    
    if avg_latency > 0:
        # Score decreases as latency increases
        latency_val = max(0, 100 * (1 - (avg_latency / max_latency)))
    else:
        # No data, assume neutral
        latency_val = 50.0
        
    if avg_latency > max_latency:
        warnings.append(f"Latency ({avg_latency:.0f}ms) exceeds max ({max_latency:.0f}ms)")

    # 4. Region Score (0-100)
    cluster_region = cluster_data.get("region")
    if region_preference and cluster_region == region_preference:
        region_val = 100
        reasons.append("Region match")
    elif not region_preference:
        region_val = 100
    else:
        region_val = 0
        if not cfg.commercial_global_routing_allow_cross_region:
            warnings.append(f"Cross-region not allowed (Cluster: {cluster_region}, Target: {region_preference})")

    # 5. Priority Score (0-100)
    # Priority in registry: lower is better (standard priority logic)
    # Here we normalize: 1 is best (100 pts), 1000 is worst (0 pts)
    priority = int(cluster_data.get("priority", 100))
    priority_val = max(0, 100 * (1 - (priority / 1000)))

    # Weighted Sum
    total_score = (
        (margin_val * w_margin) +
        (latency_val * w_latency) +
        (health_val * w_health) +
        (region_val * w_region) +
        (priority_val * w_priority)
    )
    
    return {
        "cluster_id": cluster_data["cluster_id"],
        "score": round(total_score, 2),
        "margin_score": round(margin_val * w_margin, 2),
        "latency_score": round(latency_val * w_latency, 2),
        "health_score": round(health_val * w_health, 2),
        "region_score": round(region_val * w_region, 2),
        "priority_score": round(priority_val * w_priority, 2),
        "reasons": reasons,
        "warnings": warnings,
        "status": status,
        "region": cluster_region,
        "actual_margin_brl": actual_margin,
        "avg_latency_ms": avg_latency,
    }


async def rank_clusters(
    db: AsyncSession,
    *,
    tenant_id: str | None = None,
    region_preference: str | None = None,
    settings: Settings | None = None,
    qos_tier: Any | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    overview = await summarize_federated_overview(db, settings=cfg)
    clusters = overview.get("clusters", [])
    
    ranked = []
    rejected = []
    
    for cluster in clusters:
        cluster_id = cluster["cluster_id"]

        # Phase 20: QoS Tier Hard Rejections
        if qos_tier:
            if not qos_tier.allow_cross_cluster:
                rejected.append({
                    "cluster_id": cluster_id,
                    "reason": "qos_cross_cluster_forbidden",
                    "message": f"QoS Tier {qos_tier.name} forbids cross-cluster routing"
                })
                continue
            
            if cluster.get("status") == "degraded" and not qos_tier.allow_degraded_cluster:
                rejected.append({
                    "cluster_id": cluster_id,
                    "reason": "qos_degraded_cluster_forbidden",
                    "message": f"QoS Tier {qos_tier.name} forbids degraded clusters"
                })
                continue
        
        # Validation: Tenant Scope
        allowed, reason = validate_tenant_scope(cluster.get("tenant_scope_json"), tenant_id)
        if not allowed:
            rejected.append({
                "cluster_id": cluster_id,
                "reason": "tenant_scope_rejected",
                "message": reason
            })
            continue
            
        # Validation: Health
        if cfg.commercial_global_routing_require_healthy_cluster and cluster.get("status") not in {"active", "degraded"}:
            rejected.append({
                "cluster_id": cluster_id,
                "reason": "unhealthy_cluster",
                "message": f"Cluster status is {cluster.get('status')}"
            })
            continue

        # Validation: Cross-Region
        if not cfg.commercial_global_routing_allow_cross_region and region_preference and cluster.get("region") != region_preference:
            rejected.append({
                "cluster_id": cluster_id,
                "reason": "cross_region_rejected",
                "message": f"Cross-region forbidden (Cluster: {cluster.get('region')}, Target: {region_preference})"
            })
            continue
            
        score_info = score_cluster(cluster, region_preference=region_preference, settings=cfg, qos_tier=qos_tier)
        ranked.append(score_info)
        
    ranked.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "mode": cfg.commercial_global_routing_mode,
        "ranked_clusters": ranked,
        "rejected_clusters": rejected,
    }


async def simulate_global_route(
    db: AsyncSession,
    *,
    tenant_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    region_preference: str | None = None,
    estimated_tokens: int = 0,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    ranking = await rank_clusters(db, tenant_id=tenant_id, region_preference=region_preference, settings=cfg)
    
    recommended = ranking["ranked_clusters"][0] if ranking["ranked_clusters"] else None
    
    return sanitize_report_payload({
        "mode": ranking["mode"],
        "recommended_cluster": recommended,
        "ranked_clusters": ranking["ranked_clusters"],
        "rejected_clusters": ranking["rejected_clusters"],
        "simulation_params": {
            "tenant_id": tenant_id,
            "provider": provider,
            "model": model,
            "region_preference": region_preference,
            "estimated_tokens": estimated_tokens,
        },
        "timestamp": utc_now().isoformat(),
        "warnings": recommended["warnings"] if recommended else ["No cluster available for routing"],
    })


async def generate_cluster_recommendations(
    db: AsyncSession,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    # General recommendations based on current state (no specific tenant)
    return await simulate_global_route(db, settings=settings)


async def get_global_router_overview(
    db: AsyncSession,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    ranking = await rank_clusters(db, settings=cfg)
    
    return sanitize_report_payload({
        "enabled": cfg.commercial_global_routing_enabled,
        "mode": cfg.commercial_global_routing_mode,
        "config": {
            "margin_weight": cfg.commercial_global_routing_margin_weight,
            "latency_weight": cfg.commercial_global_routing_latency_weight,
            "health_weight": cfg.commercial_global_routing_health_weight,
            "region_weight": cfg.commercial_global_routing_region_weight,
            "priority_weight": cfg.commercial_global_routing_priority_weight,
            "require_healthy": cfg.commercial_global_routing_require_healthy_cluster,
            "allow_cross_region": cfg.commercial_global_routing_allow_cross_region,
            "max_latency_ms": cfg.commercial_global_routing_max_latency_ms,
        },
        "clusters": ranking["ranked_clusters"],
        "rejected": ranking["rejected_clusters"],
        "timestamp": utc_now().isoformat(),
    })


def export_routing_csv(data: dict[str, Any]) -> str:
    clusters = data.get("ranked_clusters", [])
    output = io.StringIO()
    if not clusters:
        return "No data"
    
    fieldnames = ["cluster_id", "score", "status", "region", "actual_margin_brl", "avg_latency_ms"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in clusters:
        writer.writerow(row)
    return output.getvalue()


def export_routing_html(data: dict[str, Any]) -> str:
    clusters = data.get("ranked_clusters", [])
    rejected = data.get("rejected_clusters", [])
    mode = data.get("mode", "unknown")
    
    def _render_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
        if not rows:
            return "<p>No clusters.</p>"
        head = "".join(f"<th>{html.escape(f)}</th>" for f in fields)
        body = []
        for row in rows:
            cols = "".join(f"<td>{html.escape(str(row.get(f, '-')))}</td>" for f in fields)
            body.append(f"<tr>{cols}</tr>")
        return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"

    return f"""<!doctype html>
<html>
<head>
    <title>Global Routing Overview</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; color: #333; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
        th {{ background: #f4f4f4; }}
        .recommended {{ background: #e8f5e9; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Global Routing Overview ({html.escape(mode)})</h1>
    <h2>Ranked Clusters</h2>
    {_render_table(clusters, ["cluster_id", "score", "status", "region", "actual_margin_brl", "avg_latency_ms"])}
    <h2>Rejected Clusters</h2>
    {_render_table(rejected, ["cluster_id", "reason", "message"])}
</body>
</html>"""
