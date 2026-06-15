from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.billing.ai_wallet import AiWalletTransaction
from app.models.billing.request_financial import RequestFinancial
from app.models.commercial.commercial_billing_dispute import CommercialBillingDispute
from app.models.commercial.commercial_financial_anomaly import CommercialFinancialAnomaly
from app.models.commercial.commercial_qos_billing_record import CommercialQoSBillingRecord
from app.services.notifications.revenue_escalations import evaluate_escalation_policies
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class FinancialAnomalyDetectionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()

    async def detect_revenue_anomalies(self) -> list[CommercialFinancialAnomaly]:
        return await self._detect_anomalies("revenue")

    async def detect_cost_anomalies(self) -> list[CommercialFinancialAnomaly]:
        return await self._detect_anomalies("cost")

    async def detect_margin_anomalies(self) -> list[CommercialFinancialAnomaly]:
        return await self._detect_anomalies("margin")

    async def detect_wallet_debit_anomalies(self) -> list[CommercialFinancialAnomaly]:
        return await self._detect_anomalies("wallet_debit")

    async def detect_qos_billing_anomalies(self) -> list[CommercialFinancialAnomaly]:
        return await self._detect_anomalies("qos_billing")

    async def detect_dispute_anomalies(self) -> list[CommercialFinancialAnomaly]:
        return await self._detect_anomalies("dispute")

    async def _detect_anomalies(self, metric_type: str) -> list[CommercialFinancialAnomaly]:
        # 1. Get recent data (last 24h) and historical baseline (last 14 days)
        now = utc_now()
        yesterday = now - timedelta(days=1)
        baseline_start = now - timedelta(days=15)
        baseline_end = yesterday

        # This is a simplified detection: compare yesterday's aggregate with historical average
        historical_series = await self._get_historical_series(
            metric_type, baseline_start, baseline_end
        )
        recent_value = await self._get_recent_value(metric_type, yesterday, now)

        if len(historical_series) < self.settings.commercial_financial_anomaly_min_samples:
            return []

        baseline_mean = float(np.mean(historical_series))
        baseline_std = float(np.std(historical_series))
        observed = float(recent_value)

        anomalies = []

        # Z-score detection
        z_score = 0
        if baseline_std > 0:
            z_score = (observed - baseline_mean) / baseline_std

        # Percentage detection
        deviation_pct = 0
        if baseline_mean > 0:
            deviation_pct = ((observed - baseline_mean) / baseline_mean) * 100

        is_anomaly = False
        anomaly_subtype = f"{metric_type}_spike"
        severity = "low"

        if (
            abs(z_score) >= self.settings.commercial_financial_anomaly_zscore_threshold
            or abs(deviation_pct) >= self.settings.commercial_financial_anomaly_percent_threshold
        ):
            is_anomaly = True

        if is_anomaly:
            if deviation_pct < 0:
                anomaly_subtype = f"{metric_type}_drop"

            if abs(z_score) > 5 or abs(deviation_pct) > 100:
                severity = "critical"
            elif abs(z_score) > 3 or abs(deviation_pct) > 50:
                severity = "high"
            else:
                severity = "medium"

            explanation = f"Detected {anomaly_subtype} for {metric_type}. Observed: {observed:.2f}, Expected: {baseline_mean:.2f} (z-score: {z_score:.2f}, deviation: {deviation_pct:.2f}%)"

            anomaly = CommercialFinancialAnomaly(
                anomaly_type=anomaly_subtype,
                severity=severity,
                detected_at=now,
                observed_value_brl=Decimal(str(round(observed, 6))),
                expected_value_brl=Decimal(str(round(baseline_mean, 6))),
                deviation_percent=deviation_pct,
                z_score=z_score,
                explanation=explanation,
                status="open",
            )
            self.session.add(anomaly)
            anomalies.append(anomaly)
            await self.session.commit()
            await self.session.refresh(anomaly)
            if severity == "critical":
                try:
                    await evaluate_escalation_policies(
                        self.session,
                        source_type="anomaly",
                        source_id=anomaly.id,
                        severity=severity,
                        summary=explanation,
                        recommendation="Investigate the critical anomaly and verify financial controls.",
                        metadata=anomaly.metadata_json or {},
                        trigger_type="critical_anomaly",
                        timestamp=anomaly.detected_at,
                    )
                except Exception:
                    pass
            elif anomaly_subtype == "margin_drop" and severity in {"high", "critical"}:
                try:
                    await evaluate_escalation_policies(
                        self.session,
                        source_type="anomaly",
                        source_id=anomaly.id,
                        severity=severity,
                        summary=explanation,
                        recommendation="Investigate the margin collapse and verify pricing and cost drift.",
                        metadata=anomaly.metadata_json or {},
                        trigger_type="margin_collapse",
                        timestamp=anomaly.detected_at,
                    )
                except Exception:
                    pass

        return anomalies

    async def _get_historical_series(
        self, metric_type: str, start: datetime, end: datetime
    ) -> list[float]:
        # Implementation similar to forecasting series but for baseline
        if metric_type == "revenue":
            stmt = (
                select(func.sum(RequestFinancial.customer_price_brl))
                .where(RequestFinancial.created_at >= start, RequestFinancial.created_at <= end)
                .group_by(func.date_trunc("day", RequestFinancial.created_at))
            )
        elif metric_type == "cost":
            stmt = (
                select(func.sum(RequestFinancial.provider_cost_brl))
                .where(RequestFinancial.created_at >= start, RequestFinancial.created_at <= end)
                .group_by(func.date_trunc("day", RequestFinancial.created_at))
            )
        elif metric_type == "margin":
            stmt = (
                select(func.sum(RequestFinancial.gross_profit_brl))
                .where(RequestFinancial.created_at >= start, RequestFinancial.created_at <= end)
                .group_by(func.date_trunc("day", RequestFinancial.created_at))
            )
        elif metric_type == "wallet_debit":
            stmt = (
                select(func.sum(AiWalletTransaction.amount_brl))
                .where(
                    AiWalletTransaction.type == "debit",
                    AiWalletTransaction.created_at >= start,
                    AiWalletTransaction.created_at <= end,
                )
                .group_by(func.date_trunc("day", AiWalletTransaction.created_at))
            )
        elif metric_type == "qos_billing":
            stmt = (
                select(func.sum(CommercialQoSBillingRecord.billable_amount_brl))
                .where(
                    CommercialQoSBillingRecord.created_at >= start,
                    CommercialQoSBillingRecord.created_at <= end,
                )
                .group_by(func.date_trunc("day", CommercialQoSBillingRecord.created_at))
            )
        elif metric_type == "dispute":
            stmt = (
                select(func.count(CommercialBillingDispute.id))
                .where(
                    CommercialBillingDispute.created_at >= start,
                    CommercialBillingDispute.created_at <= end,
                )
                .group_by(func.date_trunc("day", CommercialBillingDispute.created_at))
            )
        else:
            return []

        result = await self.session.execute(stmt)
        return [float(row[0]) for row in result.all()]

    async def _get_recent_value(self, metric_type: str, start: datetime, end: datetime) -> float:
        if metric_type == "revenue":
            stmt = select(func.sum(RequestFinancial.customer_price_brl)).where(
                RequestFinancial.created_at >= start, RequestFinancial.created_at <= end
            )
        elif metric_type == "cost":
            stmt = select(func.sum(RequestFinancial.provider_cost_brl)).where(
                RequestFinancial.created_at >= start, RequestFinancial.created_at <= end
            )
        elif metric_type == "margin":
            stmt = select(func.sum(RequestFinancial.gross_profit_brl)).where(
                RequestFinancial.created_at >= start, RequestFinancial.created_at <= end
            )
        elif metric_type == "wallet_debit":
            stmt = select(func.sum(AiWalletTransaction.amount_brl)).where(
                AiWalletTransaction.type == "debit",
                AiWalletTransaction.created_at >= start,
                AiWalletTransaction.created_at <= end,
            )
        elif metric_type == "qos_billing":
            stmt = select(func.sum(CommercialQoSBillingRecord.billable_amount_brl)).where(
                CommercialQoSBillingRecord.created_at >= start,
                CommercialQoSBillingRecord.created_at <= end,
            )
        elif metric_type == "dispute":
            stmt = select(func.count(CommercialBillingDispute.id)).where(
                CommercialBillingDispute.created_at >= start,
                CommercialBillingDispute.created_at <= end,
            )
        else:
            return 0.0

        result = await self.session.execute(stmt)
        val = result.scalar()
        return float(val or 0.0)

    async def summarize_anomalies(self) -> dict[str, Any]:
        stmt = select(
            CommercialFinancialAnomaly.status, func.count(CommercialFinancialAnomaly.id)
        ).group_by(CommercialFinancialAnomaly.status)

        result = await self.session.execute(stmt)
        summary = {row.status: row[1] for row in result.all()}

        stmt_crit = select(func.count(CommercialFinancialAnomaly.id)).where(
            CommercialFinancialAnomaly.severity == "critical",
            CommercialFinancialAnomaly.status == "open",
        )
        res_crit = await self.session.execute(stmt_crit)
        summary["critical_open"] = res_crit.scalar() or 0

        return summary
