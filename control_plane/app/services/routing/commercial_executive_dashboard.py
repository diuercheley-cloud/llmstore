from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.models.admin_action_log import AdminActionLog
from app.models.commercial_routing_event import CommercialRoutingEvent
from app.services.routing.commercial_canary_promotion import CommercialCanaryPromotionService
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class CommercialExecutiveDashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def get_overview(
        self, 
        hours: int = 24,
        client_id: Optional[uuid.UUID] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Returns a consolidated executive overview of profitability and drift.
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # 1. Profitability Overview
        profitability = await self.get_profitability_overview(since, client_id, provider, model)
        
        # 2. Drift Overview
        drift = await self.get_drift_overview(since, client_id, provider, model)
        
        # 3. Clients Profitability
        clients = await self.summarize_clients_profitability(since, limit=10, client_id=client_id, provider=provider, model=model)
        
        # 4. Providers Profitability
        providers = await self.summarize_providers_profitability(since, limit=10, client_id=client_id, provider=provider, model=model)
        
        # 5. Canary Health
        canaries = await self.summarize_canary_health()
        
        # 6. Anomalies
        anomalies = await self.detect_anomalies(since, profitability, drift)
        
        # 7. Recommendations
        recommendations = await self.generate_executive_recommendations(anomalies, canaries)
        
        # 8. Global Routing (Dry-Run)
        from app.services.routing import commercial_global_router
        global_routing = await commercial_global_router.get_global_router_overview(self.db)
        
        # 9. Geo-Aware Routing (Dry-Run)
        geo_routing = await self.get_geo_routing_summary()
        
        # 10. Live Balancing (Dry-Run)
        live_balancing = await self.get_live_balancing_summary()
        
        # 11. QoS / SLA Routing (Phase 20)
        qos_sla = await self.get_qos_sla_summary(since)
        
        # 12. Infrastructure Simulation (Phase 21.1)
        infra_sim = await self.get_infra_simulation_summary()

        # 13. Revenue Forecasting (Phase 28)
        revenue_forecast = await self.get_revenue_forecast_summary()

        # 14. Financial Anomalies (Phase 28)
        financial_anomalies = await self.get_financial_anomalies_summary()
        
        # 15. Revenue Protection (Phase 29)
        revenue_protection = await self.get_revenue_protection_summary()
        
        return {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "period_hours": hours,
            "filters": {
                "client_id": str(client_id) if client_id else None,
                "provider": provider,
                "model": model
            },
            "profitability": profitability,
            "drift": drift,
            "clients": clients,
            "providers": providers,
            "canaries": canaries,
            "anomalies": anomalies,
            "recommendations": recommendations,
            "global_routing": global_routing,
            "geo_routing": geo_routing,
            "live_balancing": live_balancing,
            "qos_sla": qos_sla,
            "infra_simulation": infra_sim,
            "revenue_forecast": revenue_forecast,
            "financial_anomalies": financial_anomalies,
            "revenue_protection": revenue_protection,
        }

    async def get_revenue_protection_summary(self) -> Dict[str, Any]:
        from app.services.billing.revenue_protection import summarize_protection_status

        return await summarize_protection_status(self.db)

    async def get_revenue_forecast_summary(self) -> Dict[str, Any]:
        from app.models.commercial_revenue_forecast import CommercialRevenueForecast
        
        stmt = select(CommercialRevenueForecast).order_by(CommercialRevenueForecast.created_at.desc())
        result = await self.db.execute(stmt)
        forecasts = result.scalars().all()
        
        summary = {
            "next_30_days_revenue": 0.0,
            "next_30_days_margin": 0.0,
            "confidence": "low",
            "last_updated": None
        }
        
        found_rev = False
        found_marg = False
        for f in forecasts:
            if f.forecast_type == "revenue" and not found_rev:
                summary["next_30_days_revenue"] = float(f.predicted_amount_brl)
                summary["confidence"] = f.confidence
                summary["last_updated"] = f.created_at.isoformat()
                found_rev = True
            elif f.forecast_type == "margin" and not found_marg:
                summary["next_30_days_margin"] = float(f.predicted_amount_brl)
                found_marg = True
            if found_rev and found_marg:
                break
        
        return summary

    async def get_financial_anomalies_summary(self) -> Dict[str, Any]:
        from app.models.commercial_financial_anomaly import CommercialFinancialAnomaly
        
        stmt = select(CommercialFinancialAnomaly).order_by(CommercialFinancialAnomaly.detected_at.desc()).limit(10)
        result = await self.db.execute(stmt)
        anomalies = result.scalars().all()
        
        open_anomalies = [a for a in anomalies if a.status == "open"]
        critical_count = sum(1 for a in open_anomalies if a.severity == "critical")
        
        return {
            "total_open_count": len(open_anomalies),
            "critical_open_count": critical_count,
            "recent_anomalies": [
                {
                    "id": str(a.id),
                    "type": a.anomaly_type,
                    "severity": a.severity,
                    "observed": float(a.observed_value_brl),
                    "expected": float(a.expected_value_brl),
                    "detected_at": a.detected_at.isoformat()
                }
                for a in open_anomalies[:5]
            ],
            "health_badge": "SAFE" if not open_anomalies else "WARNING" if critical_count == 0 else "CRITICAL"
        }

    async def get_infra_simulation_summary(self) -> Dict[str, Any]:
        from app.models.commercial_infra_simulation import CommercialInfrastructureSimulation
        
        stmt = select(CommercialInfrastructureSimulation).order_by(CommercialInfrastructureSimulation.created_at.desc()).limit(10)
        result = await self.db.execute(stmt)
        sims = result.scalars().all()
        
        blocked = [s for s in sims if s.safety_gate_status == "blocked"]
        requires_approval = [s for s in sims if s.safety_gate_status == "requires_approval"]
        
        return {
            "enabled": self.settings.commercial_infra_simulation_enabled,
            "mode": self.settings.commercial_infra_execution_mode,
            "recent_simulations": [
                {
                    "id": str(s.id),
                    "type": s.simulation_type,
                    "status": s.safety_gate_status,
                    "blast_radius": s.blast_radius,
                    "cost_impact": s.predicted_cost_impact_brl,
                    "created_at": s.created_at.isoformat()
                }
                for s in sims
            ],
            "blocked_count": len(blocked),
            "approval_required_count": len(requires_approval),
            "health_badge": "SAFE" if not blocked and not requires_approval else "WARNING" if requires_approval else "CRITICAL"
        }

    async def get_qos_sla_summary(self, since: datetime) -> Dict[str, Any]:
        from app.models.commercial_qos_tier import CommercialQoSTier
        
        res_tiers = await self.db.execute(select(CommercialQoSTier))
        tiers = list(res_tiers.scalars().all())
        
        stmt = select(
            CommercialRoutingEvent.qos_tier,
            func.count(CommercialRoutingEvent.id).label("total"),
            func.count(CommercialRoutingEvent.id).filter(CommercialRoutingEvent.sla_pass == True).label("passed"),
            func.avg(CommercialRoutingEvent.latency_ms).label("avg_latency"),
            func.avg(CommercialRoutingEvent.actual_margin_percent).label("avg_margin")
        ).where(
            CommercialRoutingEvent.created_at >= since,
            CommercialRoutingEvent.qos_tier.is_not(None)
        ).group_by(CommercialRoutingEvent.qos_tier)
        
        res_stats = await self.db.execute(stmt)
        stats = {row.qos_tier: row for row in res_stats.all()}
        
        tier_summaries = []
        for tier in tiers:
            s = stats.get(tier.name)
            total = s.total if s else 0
            passed = s.passed if s else 0
            pass_rate = (passed / total * 100) if total > 0 else 100.0
            
            tier_summaries.append({
                "name": tier.name,
                "enabled": tier.enabled,
                "total_requests": total,
                "sla_pass_rate": round(pass_rate, 2),
                "avg_latency_ms": round(float(s.avg_latency or 0), 2) if s else 0,
                "avg_margin_percent": round(float(s.avg_margin or 0), 2) if s else 0,
                "target_latency_ms": tier.target_latency_ms,
            })
            
        return {
            "tiers": tier_summaries,
            "overall_sla_pass_rate": round(sum(t["sla_pass_rate"] for t in tier_summaries) / len(tier_summaries), 2) if tier_summaries else 100.0
        }

    async def get_geo_routing_summary(self) -> Dict[str, Any]:
        from app.models.commercial_cluster_registry import CommercialClusterRegistry
        res = await self.db.execute(select(CommercialClusterRegistry))
        all_clusters = list(res.scalars().all())
        
        return {
            "enabled": self.settings.commercial_geo_routing_enabled,
            "mode": self.settings.commercial_geo_routing_mode,
            "cluster_count": len(all_clusters),
            "cross_ocean_allowed": self.settings.commercial_geo_routing_allow_cross_ocean
        }

    async def get_live_balancing_summary(self) -> Dict[str, Any]:
        return {
            "enabled": self.settings.commercial_live_balancing_enabled,
            "mode": self.settings.commercial_live_balancing_mode,
            "min_margin_percent": self.settings.commercial_live_balancing_min_margin_percent,
            "rebalance_interval_seconds": self.settings.commercial_live_balancing_rebalance_interval_seconds
        }

    async def get_profitability_overview(
        self, 
        since: datetime,
        client_id: Optional[uuid.UUID] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        filters = [CommercialRoutingEvent.created_at >= since]
        if date_to:
            filters.append(CommercialRoutingEvent.created_at < date_to)
        if client_id:
            filters.append(CommercialRoutingEvent.client_id == client_id)
        if provider:
            filters.append(CommercialRoutingEvent.selected_provider == provider)
        if model:
            filters.append(CommercialRoutingEvent.selected_model == model)

        stmt = select(
            func.sum(CommercialRoutingEvent.actual_revenue_brl).label("actual_revenue"),
            func.sum(CommercialRoutingEvent.actual_cost_brl).label("actual_cost"),
            func.sum(CommercialRoutingEvent.estimated_revenue_brl).label("estimated_revenue"),
            func.sum(CommercialRoutingEvent.estimated_cost_brl).label("estimated_cost"),
            func.count(CommercialRoutingEvent.id).label("total_requests"),
            func.count(CommercialRoutingEvent.id).filter(CommercialRoutingEvent.fallback_used == True).label("fallbacks"),
            func.count(CommercialRoutingEvent.id).filter(CommercialRoutingEvent.blocked == True).label("blocks"),
            func.avg(CommercialRoutingEvent.latency_ms).label("avg_latency"),
        ).where(*filters)

        res = await self.db.execute(stmt)
        row = res.one()

        actual_rev = float(row.actual_revenue or 0)
        actual_cost = float(row.actual_cost or 0)
        actual_margin = actual_rev - actual_cost
        actual_margin_pct = (actual_margin / actual_rev * 100) if actual_rev > 0 else 0.0

        est_rev = float(row.estimated_revenue or 0)
        est_cost = float(row.estimated_cost or 0)
        est_margin = est_rev - est_cost
        
        est_error_pct = 0.0
        if actual_rev > 0:
            est_error_pct = abs(actual_margin - est_margin) / actual_rev * 100

        total = row.total_requests or 0
        fallback_rate = (row.fallbacks / total * 100) if total > 0 else 0.0
        block_rate = (row.blocks / total * 100) if total > 0 else 0.0

        return {
            "actual_revenue_brl": round(actual_rev, 4),
            "actual_cost_brl": round(actual_cost, 4),
            "actual_margin_brl": round(actual_margin, 4),
            "actual_margin_percent": round(actual_margin_pct, 2),
            "estimated_margin_brl": round(est_margin, 4),
            "estimation_error_percent": round(est_error_pct, 2),
            "total_requests": total,
            "fallback_rate": round(fallback_rate, 2),
            "block_rate": round(block_rate, 2),
            "avg_latency_ms": round(float(row.avg_latency or 0), 2),
        }

    async def get_drift_overview(
        self, 
        since: datetime,
        client_id: Optional[uuid.UUID] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculates drift by comparing recent performance vs previous period of same length.
        """
        current_end = date_to or datetime.now(timezone.utc)
        period_len = current_end - since
        prev_since = since - period_len
        
        # Current period metrics
        current = await self._query_basic_metrics(since, current_end, client_id, provider, model)
        # Previous period metrics
        previous = await self._query_basic_metrics(prev_since, since, client_id, provider, model)
        
        def calc_drift(curr: float, prev: float) -> float:
            if prev <= 0: return 0.0
            return ((curr - prev) / prev) * 100

        return {
            "cost_drift_percent": round(calc_drift(current["avg_cost"], previous["avg_cost"]), 2),
            "margin_drift_percent": round(calc_drift(current["avg_margin_pct"], previous["avg_margin_pct"]), 2),
            "latency_drift_percent": round(calc_drift(current["avg_latency"], previous["avg_latency"]), 2),
        }

    async def _query_basic_metrics(self, start: datetime, end: datetime, client_id, provider, model) -> Dict[str, float]:
        filters = [CommercialRoutingEvent.created_at >= start, CommercialRoutingEvent.created_at < end]
        if client_id: filters.append(CommercialRoutingEvent.client_id == client_id)
        if provider: filters.append(CommercialRoutingEvent.selected_provider == provider)
        if model: filters.append(CommercialRoutingEvent.selected_model == model)

        stmt = select(
            func.avg(CommercialRoutingEvent.actual_cost_brl).label("avg_cost"),
            func.avg(CommercialRoutingEvent.actual_margin_percent).label("avg_margin_pct"),
            func.avg(CommercialRoutingEvent.latency_ms).label("avg_latency"),
        ).where(*filters)

        res = await self.db.execute(stmt)
        row = res.one()
        return {
            "avg_cost": float(row.avg_cost or 0),
            "avg_margin_pct": float(row.avg_margin_pct or 0),
            "avg_latency": float(row.avg_latency or 0),
        }

    async def summarize_clients_profitability(
        self,
        since: datetime,
        limit: int = 10,
        client_id: Optional[uuid.UUID] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        filters = [
            CommercialRoutingEvent.created_at >= since,
            CommercialRoutingEvent.client_id.is_not(None),
        ]
        if date_to:
            filters.append(CommercialRoutingEvent.created_at < date_to)
        if client_id:
            filters.append(CommercialRoutingEvent.client_id == client_id)
        if provider:
            filters.append(CommercialRoutingEvent.selected_provider == provider)
        if model:
            filters.append(CommercialRoutingEvent.selected_model == model)
        stmt = select(
            CommercialRoutingEvent.client_id,
            func.sum(CommercialRoutingEvent.actual_revenue_brl).label("revenue"),
            func.sum(CommercialRoutingEvent.actual_cost_brl).label("cost"),
            func.sum(CommercialRoutingEvent.actual_margin_brl).label("margin"),
            func.avg(CommercialRoutingEvent.actual_margin_percent).label("margin_pct"),
            func.count(CommercialRoutingEvent.id).label("requests")
        ).where(*filters).group_by(CommercialRoutingEvent.client_id).order_by(desc("margin")).limit(limit)

        res = await self.db.execute(stmt)
        return [
            {
                "client_id": str(row.client_id),
                "revenue_brl": round(float(row.revenue or 0), 4),
                "cost_brl": round(float(row.cost or 0), 4),
                "margin_brl": round(float(row.margin or 0), 4),
                "margin_percent": round(float(row.margin_pct or 0), 2),
                "request_count": row.requests
            }
            for row in res.all()
        ]

    async def summarize_providers_profitability(
        self,
        since: datetime,
        limit: int = 10,
        client_id: Optional[uuid.UUID] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        filters = [
            CommercialRoutingEvent.created_at >= since,
            CommercialRoutingEvent.selected_provider.is_not(None),
        ]
        if date_to:
            filters.append(CommercialRoutingEvent.created_at < date_to)
        if client_id:
            filters.append(CommercialRoutingEvent.client_id == client_id)
        if provider:
            filters.append(CommercialRoutingEvent.selected_provider == provider)
        if model:
            filters.append(CommercialRoutingEvent.selected_model == model)
        stmt = select(
            CommercialRoutingEvent.selected_provider,
            func.sum(CommercialRoutingEvent.actual_revenue_brl).label("revenue"),
            func.sum(CommercialRoutingEvent.actual_cost_brl).label("cost"),
            func.sum(CommercialRoutingEvent.actual_margin_brl).label("margin"),
            func.avg(CommercialRoutingEvent.actual_margin_percent).label("margin_pct"),
            func.avg(CommercialRoutingEvent.latency_ms).label("latency")
        ).where(*filters).group_by(CommercialRoutingEvent.selected_provider).order_by(desc("margin")).limit(limit)

        res = await self.db.execute(stmt)
        return [
            {
                "provider": row.selected_provider,
                "revenue_brl": round(float(row.revenue or 0), 4),
                "cost_brl": round(float(row.cost or 0), 4),
                "margin_brl": round(float(row.margin or 0), 4),
                "margin_percent": round(float(row.margin_pct or 0), 2),
                "avg_latency_ms": round(float(row.latency or 0), 2)
            }
            for row in res.all()
        ]

    async def summarize_canary_health(self) -> Dict[str, Any]:
        canary_service = CommercialCanaryPromotionService(self.db)
        promotions = await canary_service.list_active_promotions()
        
        rollbacks_stmt = select(func.count(AdminActionLog.id)).where(
            AdminActionLog.action == "canary_auto_rollback",
            AdminActionLog.created_at >= datetime.now(timezone.utc) - timedelta(hours=self.settings.commercial_anomaly_lookback_hours)
        )
        res_rollbacks = await self.db.execute(rollbacks_stmt)
        rollback_count = res_rollbacks.scalar() or 0

        healthy_count = sum(1 for p in promotions if p["slo_pass"])
        
        return {
            "active_canaries_count": len(promotions),
            "healthy_canaries_count": healthy_count,
            "pass_rate_percent": round(healthy_count / len(promotions) * 100, 2) if promotions else 100.0,
            "auto_rollback_count_24h": rollback_count,
            "active_promotions": promotions[:5] # Limit detail to top 5
        }

    async def detect_anomalies(self, since: datetime, profitability: Dict[str, Any], drift: Dict[str, Any]) -> List[Dict[str, Any]]:
        anomalies = []
        
        # 1. Cost Drift Anomaly
        if abs(drift["cost_drift_percent"]) >= self.settings.commercial_cost_drift_alert_percent:
            anomalies.append({
                "type": "cost_drift",
                "severity": "WARNING" if abs(drift["cost_drift_percent"]) < 50 else "CRITICAL",
                "message": f"Cost drift detected: {drift['cost_drift_percent']}%",
                "actual": drift["cost_drift_percent"],
                "threshold": self.settings.commercial_cost_drift_alert_percent
            })

        # 2. Margin Drift Anomaly
        if drift["margin_drift_percent"] <= -self.settings.commercial_margin_drift_alert_percent:
            anomalies.append({
                "type": "margin_drift",
                "severity": "WARNING" if drift["margin_drift_percent"] > -30 else "CRITICAL",
                "message": f"Margin drift detected: {drift['margin_drift_percent']}%",
                "actual": drift["margin_drift_percent"],
                "threshold": -self.settings.commercial_margin_drift_alert_percent
            })

        # 3. Latency Drift Anomaly
        if drift["latency_drift_percent"] >= self.settings.commercial_latency_drift_alert_percent:
            anomalies.append({
                "type": "latency_drift",
                "severity": "WARNING",
                "message": f"Latency drift detected: {drift['latency_drift_percent']}%",
                "actual": drift["latency_drift_percent"],
                "threshold": self.settings.commercial_latency_drift_alert_percent
            })

        # 4. Negative Margin Anomaly
        if self.settings.commercial_negative_margin_alert:
            stmt_neg = select(func.count(CommercialRoutingEvent.id)).where(
                CommercialRoutingEvent.created_at >= since,
                CommercialRoutingEvent.actual_margin_brl < 0
            )
            res_neg = await self.db.execute(stmt_neg)
            neg_count = res_neg.scalar() or 0
            if neg_count > 0:
                anomalies.append({
                    "type": "negative_margin",
                    "severity": "CRITICAL",
                    "message": f"Detected {neg_count} requests with negative margin",
                    "actual": neg_count,
                    "threshold": 0
                })

        # 5. Estimation Error Anomaly
        if profitability["estimation_error_percent"] >= 20.0: # Hardcoded 20% for estimation error
            anomalies.append({
                "type": "estimation_error",
                "severity": "WARNING",
                "message": f"High estimation error: {profitability['estimation_error_percent']}%",
                "actual": profitability["estimation_error_percent"],
                "threshold": 20.0
            })
            
        return anomalies

    async def generate_executive_recommendations(self, anomalies: List[Dict[str, Any]], canaries: Dict[str, Any]) -> List[Dict[str, Any]]:
        recommendations = []
        
        for anomaly in anomalies:
            if anomaly["type"] == "cost_drift":
                recommendations.append({
                    "title": "Recalibrate Provider Costs",
                    "action": "Run /admin/routing/calibration/report and apply recommendations",
                    "reason": anomaly["message"]
                })
            elif anomaly["type"] == "negative_margin":
                recommendations.append({
                    "title": "Review Pricing or Policies",
                    "action": "Increase cost_multiplier for expensive providers or update client pricing",
                    "reason": anomaly["message"]
                })
            elif anomaly["type"] == "latency_drift":
                recommendations.append({
                    "title": "Investigate Provider Latency",
                    "action": "Reduce weight for high-latency providers in commercial_ranker",
                    "reason": anomaly["message"]
                })

        if canaries["active_canaries_count"] > 0 and canaries["pass_rate_percent"] < 100:
             recommendations.append({
                "title": "Review Failing Canaries",
                "action": "Check SLO details and consider manual rollback if auto-rollback didn't trigger",
                "reason": f"Only {canaries['pass_rate_percent']}% of canaries are healthy"
            })
             
        if canaries["auto_rollback_count_24h"] > 0:
            recommendations.append({
                "title": "Audit Auto-Rollbacks",
                "action": "Review failure reasons for recent rollbacks in AdminActionLog",
                "reason": f"Detected {canaries['auto_rollback_count_24h']} auto-rollbacks in the last 24h"
            })

        return recommendations
