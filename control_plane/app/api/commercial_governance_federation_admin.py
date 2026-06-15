# Owner: commercial-ops
import csv
import html
import io
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from app.models.commercial.commercial_governance_federation import (
    CommercialGovernanceFederationPeer,
)
from app.services.auth import require_admin
from app.services.governance.federated_audit import FederatedAuditService
from app.services.governance.governance_consistency import GovernanceConsistencyService
from app.services.governance.policy_federation import PolicyFederationService
from app.services.runtime_dependencies import get_db_session
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/admin/governance/federation",
    tags=["admin", "governance", "federation"],
    dependencies=[Depends(require_admin)],
)

federation_service = PolicyFederationService()
audit_service = FederatedAuditService()
consistency_service = GovernanceConsistencyService()


class RegisterPeerPayload(BaseModel):
    peer_cluster_id: str = Field(min_length=1, max_length=255)
    region: str | None = None
    environment: str = "local"
    base_url: str | None = None
    sync_mode: str = "manual"
    trust_level: str = "trusted"
    status: str = "active"
    metadata_json: dict[str, Any] | None = None


class SyncPayload(BaseModel):
    peer_cluster_id: str
    bundle_id: uuid.UUID
    direction: str = "outbound"


class IngestPolicyPayload(BaseModel):
    payload: dict[str, Any]
    peer_token: str | None = None
    peer_signature: str | None = None


class IngestAuditPayload(BaseModel):
    events: list[dict[str, Any]]
    source_cluster_id: str
    peer_token: str | None = None


@router.get("/peers")
async def list_peers(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(
        select(CommercialGovernanceFederationPeer).order_by(
            CommercialGovernanceFederationPeer.created_at.desc()
        )
    )
    peers = result.scalars().all()
    return peers


@router.post("/peers", status_code=201)
async def register_peer(
    payload: RegisterPeerPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        peer = await federation_service.register_governance_peer(
            db=db,
            peer_cluster_id=payload.peer_cluster_id,
            environment=payload.environment,
            region=payload.region,
            base_url=payload.base_url,
            sync_mode=payload.sync_mode,
            trust_level=payload.trust_level,
            status=payload.status,
            metadata_json=payload.metadata_json,
        )
        await db.commit()
        await db.refresh(peer)
        return peer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sync")
async def sync_policy(
    payload: SyncPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        sync = await federation_service.sync_policy_bundle(
            db=db,
            peer_cluster_id=payload.peer_cluster_id,
            bundle_id=payload.bundle_id,
            direction=payload.direction,
        )
        await db.commit()
        await db.refresh(sync)
        return sync
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ingest-policy")
async def ingest_policy(
    payload: IngestPolicyPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        result = await federation_service.ingest_policy_bundle_from_peer(
            db=db,
            payload=payload.payload,
            peer_token=payload.peer_token,
            peer_signature=payload.peer_signature,
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ingest-audit")
async def ingest_audit(
    payload: IngestAuditPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        result = await audit_service.ingest_audit_events(
            db=db,
            events=payload.events,
            source_cluster_id=payload.source_cluster_id,
            peer_token=payload.peer_token,
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def federation_status(db: AsyncSession = Depends(get_db_session)):
    return await federation_service.summarize_federation_status(db)


@router.get("/consistency")
async def consistency_report(db: AsyncSession = Depends(get_db_session)):
    return await consistency_service.generate_consistency_report(db)


@router.get("/audit-trail")
async def audit_trail(
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db_session),
):
    return await audit_service.summarize_federated_audit(db, limit=limit)


@router.get("/export")
async def export_federation(
    format: str = Query(default="json", pattern="^(json|csv|html)$"),
    db: AsyncSession = Depends(get_db_session),
):
    status_data = await federation_service.summarize_federation_status(db)
    consistency = await consistency_service.generate_consistency_report(db)
    audit_summary = await audit_service.summarize_federated_audit(db, limit=50)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "federation": status_data,
        "consistency": consistency,
        "audit": audit_summary,
    }

    if format == "json":
        content = json.dumps(report, indent=2, default=str).encode("utf-8")
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=governance-federation.json"},
        )

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["section", "key", "value"])
        _flatten_to_csv(report, writer)
        content = output.getvalue().encode("utf-8")
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=governance-federation.csv"},
        )

    html_content = _render_federation_html(report)
    return Response(
        content=html_content.encode("utf-8"),
        media_type="text/html",
        headers={"Content-Disposition": "inline; filename=governance-federation.html"},
    )


def _flatten_to_csv(data: Any, writer: csv.writer, prefix: str = ""):
    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            _flatten_to_csv(value, writer, new_prefix)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _flatten_to_csv(item, writer, f"{prefix}[{i}]")
    else:
        writer.writerow(
            [prefix.split(".")[0] if "." not in prefix else prefix.split(".")[0], prefix, str(data)]
        )


def _render_federation_html(report: dict[str, Any]) -> str:
    fed = report.get("federation", {})
    cons = report.get("consistency", {})
    audit = report.get("audit", {})

    peers_html = ""
    for p in fed.get("peers", []):
        status_badge = p.get("status", "unknown")
        peers_html += f"<tr><td>{html.escape(p.get('peer_cluster_id', ''))}</td><td>{html.escape(p.get('region', '') or '-')}</td><td>{html.escape(p.get('environment', ''))}</td><td><span class='badge badge-{status_badge}'>{status_badge}</span></td><td>{p.get('sync_mode', '')}</td><td>{p.get('trust_level', '')}</td><td>{p.get('last_policy_sync_at', '-')}</td></tr>"

    sync_rows = ""
    for s in fed.get("recent_syncs", []):
        sync_status = s.get("status", "")
        sync_rows += (
            f"<tr><td>{html.escape(s.get('bundle_name', ''))}</td>"
            f"<td>{html.escape(s.get('bundle_version', ''))}</td>"
            f"<td>{s.get('sync_direction', '')}</td>"
            f"<td><span class='badge badge-{sync_status}'>{sync_status}</span></td>"
            f"<td>{s.get('created_at', '')}</td></tr>"
        )

    audit_rows = ""
    for ev in audit.get("recent_events", []):
        audit_rows += f"<tr><td>{html.escape(ev.get('source_cluster_id', ''))}</td><td>{html.escape(ev.get('event_type', ''))}</td><td>{ev.get('received_at', '')}</td></tr>"

    issues_rows = ""
    for issue in cons.get("compliance_consistency", {}).get("issues", []):
        issues_rows += f"<tr><td>{html.escape(issue.get('peer', ''))}</td><td>{html.escape(issue.get('issue', ''))}</td><td>{html.escape(issue.get('severity', ''))}</td><td>{html.escape(issue.get('detail', ''))}</td></tr>"

    cc = cons.get("compliance_consistency", {})
    overall = cc.get("overall_status", "unknown")
    overall_badge = "consistent" if overall == "consistent" else "inconsistent"

    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"/>
<title>Governance Federation Report</title>
<style>
  :root {{ color-scheme: light; --bg:#f6f4ef; --ink:#1d1b16; --card:#fffdf8; --line:#d8d1c3; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family: Georgia, 'Times New Roman', serif; background:var(--bg); color:var(--ink); }}
  .page {{ max-width:1200px; margin:0 auto; padding:32px; }}
  h1,h2 {{ margin:0 0 12px; }}
  h1 {{ font-size:28px; }}
  h2 {{ font-size:20px; margin-top:24px; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); }}
  th,td {{ padding:8px; border-bottom:1px solid var(--line); text-align:left; font-size:13px; }}
  th {{ background:#f3efe6; }}
  .badge {{ padding:2px 8px; border-radius:4px; font-size:11px; font-weight:700; }}
  .badge-active,.badge-consistent,.badge-success {{ background:#d1fae5; color:#065f46; }}
  .badge-degraded,.badge-conflict,.badge-pending {{ background:#fef3c7; color:#92400e; }}
  .badge-offline,.badge-failed,.badge-inconsistent {{ background:#fee2e2; color:#991b1b; }}
  .badge-disabled {{ background:#e5e7eb; color:#374151; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px; }}
  .value {{ font-size:22px; font-weight:700; }}
  .label {{ color:#6f6a5f; font-size:12px; text-transform:uppercase; }}
</style>
</head>
<body>
<div class="page">
  <h1>Governance Federation Report</h1>
  <p>Generated at {html.escape(report.get("generated_at", ""))}</p>

  <div class="grid">
    <div class="card"><div class="label">Peers</div><div class="value">{fed.get("total_peers", 0)}</div></div>
    <div class="card"><div class="label">Online</div><div class="value">{fed.get("online_peers", 0)}</div></div>
    <div class="card"><div class="label">Offline</div><div class="value">{fed.get("offline_peers", 0)}</div></div>
    <div class="card"><div class="label">Mode</div><div class="value">{html.escape(fed.get("mode", ""))}</div></div>
    <div class="card"><div class="label">Overall</div><div class="value"><span class="badge badge-{overall_badge}">{overall}</span></div></div>
  </div>

  <h2>Federation Peers</h2>
  <table><thead><tr><th>Cluster</th><th>Region</th><th>Environment</th><th>Status</th><th>Sync Mode</th><th>Trust</th><th>Last Policy Sync</th></tr></thead><tbody>{peers_html or '<tr><td colspan="7">No peers registered</td></tr>'}</tbody></table>

  <h2>Recent Policy Syncs</h2>
  <table><thead><tr><th>Bundle</th><th>Version</th><th>Direction</th><th>Status</th><th>Timestamp</th></tr></thead><tbody>{sync_rows or '<tr><td colspan="5">No syncs recorded</td></tr>'}</tbody></table>

  <h2>Compliance Issues</h2>
  <table><thead><tr><th>Peer</th><th>Issue</th><th>Severity</th><th>Detail</th></tr></thead><tbody>{issues_rows or '<tr><td colspan="4">No compliance issues</td></tr>'}</tbody></table>

  <h2>Federated Audit Events</h2>
  <table><thead><tr><th>Source Cluster</th><th>Event Type</th><th>Received</th></tr></thead><tbody>{audit_rows or '<tr><td colspan="3">No audit events</td></tr>'}</tbody></table>
</div>
</body>
</html>"""
