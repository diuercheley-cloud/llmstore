from __future__ import annotations

import csv
import html
import importlib.util
import io
import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_settings
from app.models.admin_action_log import AdminActionLog
from app.models.commercial_report_delivery_log import CommercialReportDeliveryLog
from app.models.commercial_report_schedule import CommercialReportSchedule
from app.models.commercial_routing_config import CommercialRoutingConfig
from app.models.commercial_routing_event import CommercialRoutingEvent
from app.services.routing.commercial_executive_dashboard import CommercialExecutiveDashboardService
from app.services.routing.commercial_report_email import (
    AllowlistError,
    CommercialReportEmailError,
    EmailAttachment,
    SecurityScanError,
    SMTPAuthFailure,
    SMTPTLSFailure,
    build_email_message,
    retry_send_with_backoff,
    sanitize_email_payload,
    send_report_email,
    send_report_email_dry_run,
    validate_basic_recipients,
    validate_recipient_allowlist,
)
from fastapi import HTTPException
from sqlalchemy import String, asc, case, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

REDACTION = "[REDACTED]"
SECRET_KEY_PATTERNS = {
    "api_key",
    "authorization",
    "secret",
    "token",
    "password",
    "prompt",
    "response",
    "raw_payload",
    "payload",
}
SECRET_VALUE_PATTERNS = [
    re.compile(r"authorization\s*:\s*bearer\s+[a-z0-9._-]+", re.IGNORECASE),
    re.compile(r"\bsk-[a-z0-9]{8,}\b", re.IGNORECASE),
    re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
]
PROHIBITED_EXPORT_KEYS = {
    "api_key",
    "api_keys",
    "authorization",
    "provider_secret",
    "provider_secrets",
    "prompt",
    "prompt_text",
    "full_prompt",
    "response",
    "full_response",
    "raw_payload",
    "request_body",
    "response_body",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _round_float(value: Any, digits: int = 2) -> float:
    return round(float(value or 0), digits)


def _normalize_window(
    *,
    hours: int = 24,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[datetime, datetime]:
    end = date_to or _utc_now()
    start = date_from or (end - timedelta(hours=hours))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if start >= end:
        raise HTTPException(status_code=400, detail="date_from must be earlier than date_to")
    return start, end


def _json_safe(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    return value


def _sanitize_scalar(key: str, value: Any) -> Any:
    if value is None:
        return None
    lowered_key = key.lower()
    if lowered_key in PROHIBITED_EXPORT_KEYS or any(part in lowered_key for part in SECRET_KEY_PATTERNS):
        return REDACTION
    if isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                raise HTTPException(
                    status_code=400,
                    detail=f"Export blocked by security scanner due to sensitive pattern in field '{key}'",
                )
        return value
    return value


def sanitize_report_payload(payload: Any) -> Any:
    def _walk(node: Any, parent_key: str = "") -> Any:
        if isinstance(node, dict):
            sanitized: dict[str, Any] = {}
            for key, value in node.items():
                sanitized[key] = _walk(_sanitize_scalar(str(key), value), str(key))
            return sanitized
        if isinstance(node, list):
            return [_walk(item, parent_key) for item in node]
        return _sanitize_scalar(parent_key or "value", node)

    return _walk(_json_safe(payload))


def _flatten_report_for_csv(report: dict[str, Any]) -> list[dict[str, Any]]:
    profitability = report.get("profitability", {})
    drift = report.get("drift", {})
    canaries = report.get("canaries", {})
    security = report.get("security_observations", {})
    return [
        {
            "generated_at_utc": report.get("generated_at_utc"),
            "period_start_utc": report.get("period", {}).get("date_from"),
            "period_end_utc": report.get("period", {}).get("date_to"),
            "actual_revenue_brl": profitability.get("actual_revenue_brl"),
            "actual_cost_brl": profitability.get("actual_cost_brl"),
            "actual_margin_brl": profitability.get("actual_margin_brl"),
            "actual_margin_percent": profitability.get("actual_margin_percent"),
            "estimation_error_percent": profitability.get("estimation_error_percent"),
            "cost_drift_percent": drift.get("cost_drift_percent"),
            "margin_drift_percent": drift.get("margin_drift_percent"),
            "latency_drift_percent": drift.get("latency_drift_percent"),
            "top_clients_profitable_count": len(report.get("top_clients_profitable", [])),
            "loss_clients_count": len(report.get("clients_with_loss", [])),
            "top_providers_margin_count": len(report.get("top_providers_by_margin", [])),
            "providers_with_drift_count": len(report.get("providers_with_drift", [])),
            "active_canaries_count": canaries.get("active_canaries_count", 0),
            "completed_canaries_count": canaries.get("completed_canaries_count", 0),
            "rolled_back_canaries_count": canaries.get("rolled_back_canaries_count", 0),
            "anomalies_count": len(report.get("anomalies", [])),
            "recommendations_count": len(report.get("recommendations", [])),
            "scanner_status": security.get("scanner_status"),
        }
    ]


def export_executive_report_json(report: dict[str, Any]) -> bytes:
    return json.dumps(report, ensure_ascii=True, indent=2).encode("utf-8")


def export_executive_report_csv(report: dict[str, Any]) -> str:
    rows = _flatten_report_for_csv(report)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()) if rows else [])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def export_executive_report_html(report: dict[str, Any], *, preview: bool = False) -> str:
    profitability = report.get("profitability", {})
    drift = report.get("drift", {})
    canaries = report.get("canaries", {})
    anomalies = report.get("anomalies", [])
    recommendations = report.get("recommendations", [])

    def render_list(items: list[dict[str, Any]], fields: list[str]) -> str:
        if not items:
            return "<p class='muted'>No data.</p>"
        headers = "".join(f"<th>{html.escape(field)}</th>" for field in fields)
        rows = []
        for item in items[: (5 if preview else 20)]:
            cols = "".join(f"<td>{html.escape(str(item.get(field, '-')))}</td>" for field in fields)
            rows.append(f"<tr>{cols}</tr>")
        return f"<table><thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table>"

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Commercial Executive Report</title>
    <style>
      :root {{ color-scheme: light; --bg:#f6f4ef; --ink:#1d1b16; --muted:#6f6a5f; --line:#d8d1c3; --card:#fffdf8; --accent:#0f766e; --danger:#b42318; }}
      * {{ box-sizing:border-box; }}
      body {{ margin:0; font-family: Georgia, 'Times New Roman', serif; background:var(--bg); color:var(--ink); }}
      .page {{ max-width:1100px; margin:0 auto; padding:32px; }}
      h1,h2,h3 {{ margin:0 0 12px; }}
      h1 {{ font-size:32px; }}
      h2 {{ font-size:20px; margin-top:28px; }}
      .subtitle {{ color:var(--muted); margin-bottom:24px; }}
      .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }}
      .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px; }}
      .value {{ font-size:24px; font-weight:700; }}
      .label {{ color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:0.06em; }}
      table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); }}
      th,td {{ padding:10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:14px; }}
      th {{ background:#f3efe6; }}
      ul {{ margin:0; padding-left:18px; }}
      .muted {{ color:var(--muted); }}
      .danger {{ color:var(--danger); }}
      @media print {{ body {{ background:white; }} .page {{ padding:16px; }} }}
    </style>
  </head>
  <body>
    <div class="page">
      <h1>Commercial Executive Report</h1>
      <div class="subtitle">
        Period {html.escape(str(report.get("period", {}).get("date_from", "-")))} to {html.escape(str(report.get("period", {}).get("date_to", "-")))}
        · Generated at {html.escape(str(report.get("generated_at_utc", "-")))}
      </div>
      <div class="grid">
        <div class="card"><div class="label">Revenue</div><div class="value">R$ {profitability.get("actual_revenue_brl", 0)}</div></div>
        <div class="card"><div class="label">Cost</div><div class="value">R$ {profitability.get("actual_cost_brl", 0)}</div></div>
        <div class="card"><div class="label">Margin</div><div class="value">R$ {profitability.get("actual_margin_brl", 0)}</div></div>
        <div class="card"><div class="label">Margin %</div><div class="value">{profitability.get("actual_margin_percent", 0)}%</div></div>
        <div class="card"><div class="label">Estimation Error</div><div class="value">{profitability.get("estimation_error_percent", 0)}%</div></div>
        <div class="card"><div class="label">Cost Drift</div><div class="value">{drift.get("cost_drift_percent", 0)}%</div></div>
        <div class="card"><div class="label">Margin Drift</div><div class="value">{drift.get("margin_drift_percent", 0)}%</div></div>
        <div class="card"><div class="label">Latency Drift</div><div class="value">{drift.get("latency_drift_percent", 0)}%</div></div>
      </div>
      <h2>Clients</h2>
      {render_list(report.get("top_clients_profitable", []), ["client_id", "margin_brl", "margin_percent", "request_count"])}
      <h2>Clients With Loss</h2>
      {render_list(report.get("clients_with_loss", []), ["client_id", "margin_brl", "margin_percent", "request_count"])}
      <h2>Providers</h2>
      {render_list(report.get("top_providers_by_margin", []), ["provider", "margin_brl", "margin_percent", "avg_latency_ms"])}
      <h2>Providers With Drift</h2>
      {render_list(report.get("providers_with_drift", []), ["provider", "margin_drift_percent", "cost_drift_percent", "latency_drift_percent"])}
      <h2>Canaries</h2>
      <div class="grid">
        <div class="card"><div class="label">Active</div><div class="value">{canaries.get("active_canaries_count", 0)}</div></div>
        <div class="card"><div class="label">Completed</div><div class="value">{canaries.get("completed_canaries_count", 0)}</div></div>
        <div class="card"><div class="label">Rolled Back</div><div class="value">{canaries.get("rolled_back_canaries_count", 0)}</div></div>
      </div>
      <h2>Anomalies</h2>
      <ul>{"".join(f"<li>{html.escape(item.get('message', ''))}</li>" for item in anomalies[:(5 if preview else 20)]) or "<li>None</li>"}</ul>
      <h2>Recommendations</h2>
      <ul>{"".join(f"<li>{html.escape(item.get('title', ''))}: {html.escape(item.get('action', ''))}</li>" for item in recommendations[:(5 if preview else 20)]) or "<li>None</li>"}</ul>
      <h2>Security Observations</h2>
      <ul>
        <li>Secrets, prompts, full responses, raw payloads and authorization headers are excluded from exports.</li>
        <li>Scanner status: {html.escape(str(report.get("security_observations", {}).get("scanner_status", "unknown")))}</li>
        <li>Export mode: offline-compatible and email-safe by default.</li>
      </ul>
    </div>
  </body>
</html>"""


def export_executive_report_pdf_optional(report: dict[str, Any]) -> bytes:
    if importlib.util.find_spec("weasyprint") is not None:
        from weasyprint import HTML  # type: ignore

        return HTML(string=export_executive_report_html(report)).write_pdf()
    raise HTTPException(
        status_code=501,
        detail={
            "message": "PDF export is not available because no supported PDF dependency is installed.",
            "html_preview_path": "/admin/routing/executive-dashboard/export?format=html",
        },
    )


class CommercialReportExportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.dashboard = CommercialExecutiveDashboardService(db)

    async def _query_clients(
        self,
        *,
        start: datetime,
        end: datetime,
        profitable: bool,
        limit: int,
        client_id: uuid.UUID | None,
        provider: str | None,
        model: str | None,
    ) -> list[dict[str, Any]]:
        filters = [CommercialRoutingEvent.created_at >= start, CommercialRoutingEvent.created_at < end]
        if client_id:
            filters.append(CommercialRoutingEvent.client_id == client_id)
        if provider:
            filters.append(CommercialRoutingEvent.selected_provider == provider)
        if model:
            filters.append(CommercialRoutingEvent.selected_model == model)
        margin_sum = func.sum(CommercialRoutingEvent.actual_margin_brl)
        stmt = (
            select(
                CommercialRoutingEvent.client_id,
                func.sum(CommercialRoutingEvent.actual_revenue_brl).label("revenue"),
                func.sum(CommercialRoutingEvent.actual_cost_brl).label("cost"),
                margin_sum.label("margin"),
                func.avg(CommercialRoutingEvent.actual_margin_percent).label("margin_pct"),
                func.count(CommercialRoutingEvent.id).label("requests"),
            )
            .where(*filters, CommercialRoutingEvent.client_id.is_not(None))
            .group_by(CommercialRoutingEvent.client_id)
            .having(margin_sum >= 0 if profitable else margin_sum < 0)
            .order_by(desc("margin") if profitable else asc("margin"))
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return [
            {
                "client_id": str(row.client_id),
                "revenue_brl": _round_float(row.revenue, 4),
                "cost_brl": _round_float(row.cost, 4),
                "margin_brl": _round_float(row.margin, 4),
                "margin_percent": _round_float(row.margin_pct),
                "request_count": row.requests,
            }
            for row in res.all()
        ]

    async def _query_provider_drift(
        self,
        *,
        start: datetime,
        end: datetime,
        client_id: uuid.UUID | None,
        provider: str | None,
        model: str | None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        span = end - start
        prev_start = start - span
        provider_filters = []
        if provider:
            provider_filters.append(CommercialRoutingEvent.selected_provider == provider)
        if model:
            provider_filters.append(CommercialRoutingEvent.selected_model == model)
        if client_id:
            provider_filters.append(CommercialRoutingEvent.client_id == client_id)

        def provider_query(window_start: datetime, window_end: datetime):
            return (
                select(
                    CommercialRoutingEvent.selected_provider.label("provider"),
                    func.avg(CommercialRoutingEvent.actual_cost_brl).label("avg_cost"),
                    func.avg(CommercialRoutingEvent.actual_margin_percent).label("avg_margin_pct"),
                    func.avg(CommercialRoutingEvent.latency_ms).label("avg_latency"),
                )
                .where(
                    CommercialRoutingEvent.created_at >= window_start,
                    CommercialRoutingEvent.created_at < window_end,
                    CommercialRoutingEvent.selected_provider.is_not(None),
                    *provider_filters,
                )
                .group_by(CommercialRoutingEvent.selected_provider)
            )

        current_rows = {
            row.provider: row for row in (await self.db.execute(provider_query(start, end))).all()
        }
        previous_rows = {
            row.provider: row for row in (await self.db.execute(provider_query(prev_start, start))).all()
        }

        def calc(curr: float, prev: float) -> float:
            if prev in (0, None):
                return 0.0
            return round(((curr - prev) / prev) * 100, 2)

        drift_rows = []
        for provider_name, current in current_rows.items():
            previous = previous_rows.get(provider_name)
            if previous is None:
                continue
            margin_drift = calc(float(current.avg_margin_pct or 0), float(previous.avg_margin_pct or 0))
            cost_drift = calc(float(current.avg_cost or 0), float(previous.avg_cost or 0))
            latency_drift = calc(float(current.avg_latency or 0), float(previous.avg_latency or 0))
            if (
                abs(cost_drift) >= self.settings.commercial_cost_drift_alert_percent
                or margin_drift <= -self.settings.commercial_margin_drift_alert_percent
                or latency_drift >= self.settings.commercial_latency_drift_alert_percent
            ):
                drift_rows.append(
                    {
                        "provider": provider_name,
                        "margin_drift_percent": margin_drift,
                        "cost_drift_percent": cost_drift,
                        "latency_drift_percent": latency_drift,
                    }
                )
        drift_rows.sort(key=lambda item: abs(item["cost_drift_percent"]) + abs(item["margin_drift_percent"]), reverse=True)
        return drift_rows[:limit]

    async def _canary_summary_for_report(self, *, start: datetime) -> dict[str, Any]:
        active_stmt = select(func.count(CommercialRoutingConfig.id)).where(CommercialRoutingConfig.canary_enabled.is_(True))
        completed_stmt = select(func.count(CommercialRoutingConfig.id)).where(
            CommercialRoutingConfig.canary_promotion_status == "completed"
        )
        rollback_stmt = select(func.count(CommercialRoutingConfig.id)).where(
            CommercialRoutingConfig.canary_promotion_status == "rolled_back"
        )
        recent_rollbacks_stmt = select(func.count(AdminActionLog.id)).where(
            AdminActionLog.action.in_(["canary_auto_rollback", "auto_apply_canary_rollback"]),
            AdminActionLog.created_at >= start,
        )
        active_count = (await self.db.execute(active_stmt)).scalar() or 0
        completed_count = (await self.db.execute(completed_stmt)).scalar() or 0
        rolled_back_count = (await self.db.execute(rollback_stmt)).scalar() or 0
        recent_rollback_count = (await self.db.execute(recent_rollbacks_stmt)).scalar() or 0
        base_summary = await self.dashboard.summarize_canary_health()
        return {
            **base_summary,
            "completed_canaries_count": completed_count,
            "rolled_back_canaries_count": rolled_back_count,
            "recent_rollbacks_in_period": recent_rollback_count,
        }

    async def build_executive_report_data(
        self,
        *,
        hours: int = 24,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        client_id: uuid.UUID | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        start, end = _normalize_window(hours=hours, date_from=date_from, date_to=date_to)
        profitability = await self.dashboard.get_profitability_overview(start, client_id, provider, model, date_to=end)
        drift = await self.dashboard.get_drift_overview(start, client_id, provider, model, date_to=end)
        top_clients = await self._query_clients(
            start=start,
            end=end,
            profitable=True,
            limit=10,
            client_id=client_id,
            provider=provider,
            model=model,
        )
        loss_clients = await self._query_clients(
            start=start,
            end=end,
            profitable=False,
            limit=10,
            client_id=client_id,
            provider=provider,
            model=model,
        )
        top_providers = await self.dashboard.summarize_providers_profitability(start, limit=10, client_id=client_id, provider=provider, model=model, date_to=end)
        provider_drift = await self._query_provider_drift(
            start=start,
            end=end,
            client_id=client_id,
            provider=provider,
            model=model,
        )
        canaries = await self._canary_summary_for_report(start=start)
        anomalies = await self.dashboard.detect_anomalies(start, profitability, drift)
        recommendations = await self.dashboard.generate_executive_recommendations(anomalies, canaries)
        report = {
            "generated_at_utc": _utc_now().isoformat(),
            "period": {
                "hours": round((end - start).total_seconds() / 3600, 2),
                "date_from": start.isoformat(),
                "date_to": end.isoformat(),
            },
            "filters": {
                "client_id": str(client_id) if client_id else None,
                "provider": provider,
                "model": model,
            },
            "profitability": profitability,
            "drift": drift,
            "top_clients_profitable": top_clients,
            "clients_with_loss": loss_clients,
            "top_providers_by_margin": top_providers,
            "providers_with_drift": provider_drift,
            "canaries": canaries,
            "anomalies": anomalies,
            "recommendations": recommendations,
            "security_observations": {
                "scanner_status": "passed",
                "notes": [
                    "Exports redact or reject secrets and raw sensitive payloads.",
                    "Prompts and full responses are excluded from the report payload.",
                    "Email delivery is disabled or dry-run by default.",
                ],
            },
        }
        return sanitize_report_payload(report)

    async def create_schedule(self, payload: dict[str, Any], *, actor: str | None) -> CommercialReportSchedule:
        schedule = CommercialReportSchedule(
            name=payload["name"],
            enabled=bool(payload.get("enabled", True)),
            frequency=payload.get("frequency", "monthly"),
            day_of_month=payload.get("day_of_month"),
            day_of_week=payload.get("day_of_week"),
            hour_utc=payload.get("hour_utc", 8),
            recipients_json=payload.get("recipients_json") or [],
            format=payload.get("format", "html"),
            filters_json=payload.get("filters_json") or {},
            created_by=actor,
        )
        schedule.next_run_at = self.compute_next_run_at(schedule, reference=_utc_now())
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    def _parse_recipients(self, recipients: list[str] | None) -> list[str]:
        return [recipient.strip() for recipient in (recipients or []) if recipient and recipient.strip()]

    def _subject_for_schedule(self, schedule: CommercialReportSchedule) -> str:
        return f"Commercial Executive Report - {schedule.name}"

    def _attachment_for_report(self, report: dict[str, Any], report_format: str) -> EmailAttachment:
        if report_format == "json":
            return EmailAttachment("executive-report.json", export_executive_report_json(report), "application/json")
        if report_format == "csv":
            return EmailAttachment("executive-report.csv", export_executive_report_csv(report).encode("utf-8"), "text/csv")
        if report_format == "html":
            return EmailAttachment("executive-report.html", export_executive_report_html(report).encode("utf-8"), "text/html")
        if report_format == "pdf":
            return EmailAttachment("executive-report.pdf", export_executive_report_pdf_optional(report), "application/pdf")
        raise HTTPException(status_code=400, detail="Unsupported format. Use json, csv, html or pdf.")

    async def _create_delivery_log(
        self,
        *,
        schedule_id: uuid.UUID | None,
        report_format: str,
        recipients: list[str],
        delivery_mode: str,
        delivery_status: str,
        subject: str,
        attachment_names: list[str],
        retries: int = 0,
        error_message: str | None = None,
        delivered_at: datetime | None = None,
    ) -> CommercialReportDeliveryLog:
        delivery = CommercialReportDeliveryLog(
            schedule_id=schedule_id,
            report_format=report_format,
            recipients_json=recipients,
            delivery_mode=delivery_mode,
            delivery_status=delivery_status,
            smtp_host=self._masked_smtp_host(),
            subject=subject,
            attachment_names_json=attachment_names,
            retries=retries,
            error_message=(error_message or "")[:500] or None,
            delivered_at=delivered_at,
        )
        self.db.add(delivery)
        await self.db.flush()
        return delivery

    def _masked_smtp_host(self) -> str | None:
        host = (self.settings.commercial_report_smtp_host or "").strip()
        if not host:
            return None
        parts = host.split(".")
        head = parts[0][:1] + "***" if parts[0] else "***"
        return ".".join([head, *parts[1:]])

    def _resolve_manual_delivery_mode(self) -> str:
        if not self.settings.commercial_report_email_enabled or self.settings.commercial_report_email_mode == "disabled":
            return "disabled"
        if self.settings.commercial_report_email_mode == "dry_run":
            return "dry_run"
        if self.settings.commercial_report_email_mode == "smtp" and self.settings.commercial_report_send_real_email:
            return "smtp"
        return "blocked"

    def _resolve_automatic_delivery_mode(self) -> str:
        if not self.settings.commercial_report_email_enabled or self.settings.commercial_report_email_mode == "disabled":
            return "disabled"
        if self.settings.commercial_report_email_mode == "dry_run":
            return "dry_run"
        if self.settings.commercial_report_email_mode == "smtp" and self.settings.commercial_report_send_real_email:
            return "smtp"
        return "blocked"

    async def _deliver_report(
        self,
        *,
        schedule_id: uuid.UUID | None,
        schedule_name: str,
        recipients: list[str],
        report_format: str,
        report: dict[str, Any],
        delivery_mode: str,
    ) -> dict[str, Any]:
        subject = f"Commercial Executive Report - {schedule_name}"
        attachment = self._attachment_for_report(report, report_format)
        recipients = self._parse_recipients(recipients)
        preview_html = export_executive_report_html(report, preview=True)

        if delivery_mode == "disabled":
            delivery = await self._create_delivery_log(
                schedule_id=schedule_id,
                report_format=report_format,
                recipients=recipients,
                delivery_mode=delivery_mode,
                delivery_status="blocked",
                subject=subject,
                attachment_names=[attachment.filename],
                error_message="email_disabled: SMTP delivery is disabled",
            )
            return {
                "status": "email_disabled",
                "email_mode": self.settings.commercial_report_email_mode,
                "recipients": recipients,
                "report_format": report_format,
                "preview_html": preview_html,
                "report": report,
                "delivery_id": str(delivery.id),
            }

        if delivery_mode == "blocked":
            delivery = await self._create_delivery_log(
                schedule_id=schedule_id,
                report_format=report_format,
                recipients=recipients,
                delivery_mode=delivery_mode,
                delivery_status="blocked",
                subject=subject,
                attachment_names=[attachment.filename],
                error_message="blocked: explicit SMTP opt-in is required",
            )
            return {
                "status": "blocked",
                "email_mode": self.settings.commercial_report_email_mode,
                "recipients": recipients,
                "report_format": report_format,
                "preview_html": preview_html,
                "report": report,
                "delivery_id": str(delivery.id),
            }

        try:
            if delivery_mode == "smtp":
                recipients = validate_recipient_allowlist(recipients, settings=self.settings)
            else:
                allowlist = (self.settings.commercial_report_email_allowlist or "").strip()
                recipients = (
                    validate_recipient_allowlist(recipients, settings=self.settings)
                    if allowlist
                    else validate_basic_recipients(recipients, settings=self.settings)
                )
            sanitize_email_payload(
                {
                    "subject": subject,
                    "recipients": recipients,
                    "report_summary": report,
                    "attachment_name": attachment.filename,
                }
            )
        except AllowlistError as exc:
            delivery = await self._create_delivery_log(
                schedule_id=schedule_id,
                report_format=report_format,
                recipients=recipients,
                delivery_mode=delivery_mode,
                delivery_status="blocked",
                subject=subject,
                attachment_names=[attachment.filename],
                error_message=str(exc),
            )
            return {
                "status": "blocked",
                "email_mode": self.settings.commercial_report_email_mode,
                "recipients": recipients,
                "report_format": report_format,
                "preview_html": preview_html,
                "report": report,
                "delivery_id": str(delivery.id),
                "error": str(exc),
            }
        except SecurityScanError as exc:
            delivery = await self._create_delivery_log(
                schedule_id=schedule_id,
                report_format=report_format,
                recipients=recipients,
                delivery_mode=delivery_mode,
                delivery_status="blocked",
                subject=subject,
                attachment_names=[attachment.filename],
                error_message=str(exc),
            )
            return {
                "status": "blocked",
                "email_mode": self.settings.commercial_report_email_mode,
                "recipients": recipients,
                "report_format": report_format,
                "preview_html": preview_html,
                "report": report,
                "delivery_id": str(delivery.id),
                "error": str(exc),
            }

        if delivery_mode == "dry_run":
            try:
                send_report_email_dry_run(
                    subject=subject,
                    recipients=recipients,
                    attachments=[attachment],
                    settings=self.settings,
                )
            except SecurityScanError as exc:
                delivery = await self._create_delivery_log(
                    schedule_id=schedule_id,
                    report_format=report_format,
                    recipients=recipients,
                    delivery_mode=delivery_mode,
                    delivery_status="blocked",
                    subject=subject,
                    attachment_names=[attachment.filename],
                    error_message=str(exc),
                )
                return {
                    "status": "blocked",
                    "email_mode": self.settings.commercial_report_email_mode,
                    "recipients": recipients,
                    "report_format": report_format,
                    "preview_html": preview_html,
                    "report": report,
                    "delivery_id": str(delivery.id),
                    "error": str(exc),
                }
            delivery = await self._create_delivery_log(
                schedule_id=schedule_id,
                report_format=report_format,
                recipients=recipients,
                delivery_mode=delivery_mode,
                delivery_status="dry_run",
                subject=subject,
                attachment_names=[attachment.filename],
            )
            return {
                "status": "would_send",
                "email_mode": self.settings.commercial_report_email_mode,
                "recipients": recipients,
                "report_format": report_format,
                "preview_html": preview_html,
                "report": None,
                "delivery_id": str(delivery.id),
            }

        try:
            message = build_email_message(
                subject=subject,
                recipients=recipients,
                body_text="Attached commercial executive report. Payload sanitized for email delivery.",
                attachments=[attachment],
                settings=self.settings,
            )
        except SecurityScanError as exc:
            delivery = await self._create_delivery_log(
                schedule_id=schedule_id,
                report_format=report_format,
                recipients=recipients,
                delivery_mode=delivery_mode,
                delivery_status="blocked",
                subject=subject,
                attachment_names=[attachment.filename],
                error_message=str(exc),
            )
            return {
                "status": "blocked",
                "email_mode": self.settings.commercial_report_email_mode,
                "recipients": recipients,
                "report_format": report_format,
                "preview_html": preview_html,
                "report": report,
                "delivery_id": str(delivery.id),
                "error": str(exc),
            }
        except CommercialReportEmailError as exc:
            delivery = await self._create_delivery_log(
                schedule_id=schedule_id,
                report_format=report_format,
                recipients=recipients,
                delivery_mode=delivery_mode,
                delivery_status="failed",
                subject=subject,
                attachment_names=[attachment.filename],
                error_message=str(exc),
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        pending = await self._create_delivery_log(
            schedule_id=schedule_id,
            report_format=report_format,
            recipients=recipients,
            delivery_mode=delivery_mode,
            delivery_status="pending",
            subject=subject,
            attachment_names=[attachment.filename],
        )
        from app.services.compliance.financial_controls import evaluate_control_policy

        decision = await evaluate_control_policy(
            self.db,
            control_area="billing",
            action_type="report_email_send",
            target_type="CommercialReportSchedule",
            target_id=schedule_id,
            actor=schedule_name,
            package_type="billing_change",
            summary=f"Real report email send for schedule {schedule_name}",
            before_state={"schedule_id": str(schedule_id), "delivery_mode": delivery_mode},
            after_state={"subject": subject, "recipients": recipients, "report_format": report_format},
            payload={"schedule_id": str(schedule_id), "recipients": recipients, "delivery_mode": delivery_mode, "report_format": report_format},
            related_ids={"schedule_id": str(schedule_id), "delivery_id": str(pending.id)},
            file_refs={"attachments": [attachment.filename]},
        )
        if decision.should_block and decision.approval_chain is not None:
            pending.delivery_status = "blocked"
            pending.error_message = "pending_approval"
            await self.db.commit()
            return {
                "status": "pending_approval",
                "email_mode": self.settings.commercial_report_email_mode,
                "recipients": recipients,
                "report_format": report_format,
                "preview_html": preview_html,
                "report": None,
                "delivery_id": str(pending.id),
                "approval_chain_id": str(decision.approval_chain.id),
            }
        try:
            _, retries = await retry_send_with_backoff(
                lambda: send_report_email(message, recipients, settings=self.settings),
                retry_count=self.settings.commercial_report_email_retry_count,
                backoff_seconds=self.settings.commercial_report_email_retry_backoff_seconds,
            )
            pending.delivery_status = "sent"
            pending.retries = retries
            pending.delivered_at = _utc_now()
            return {
                "status": "sent",
                "email_mode": self.settings.commercial_report_email_mode,
                "recipients": recipients,
                "report_format": report_format,
                "preview_html": preview_html,
                "report": None,
                "delivery_id": str(pending.id),
            }
        except SMTPAuthFailure as exc:
            pending.delivery_status = "failed"
            pending.error_message = str(exc)
            raise HTTPException(status_code=502, detail="SMTP auth failure while sending commercial report email") from exc
        except SMTPTLSFailure as exc:
            pending.delivery_status = "failed"
            pending.error_message = str(exc)
            raise HTTPException(status_code=502, detail="SMTP TLS failure while sending commercial report email") from exc
        except CommercialReportEmailError as exc:
            pending.delivery_status = "failed"
            pending.error_message = str(exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    async def list_schedules(self) -> list[CommercialReportSchedule]:
        stmt = select(CommercialReportSchedule).order_by(CommercialReportSchedule.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_schedule(self, schedule_id: uuid.UUID) -> CommercialReportSchedule:
        schedule = await self.db.get(CommercialReportSchedule, schedule_id)
        if schedule is None:
            raise HTTPException(status_code=404, detail="Report schedule not found")
        return schedule

    def compute_next_run_at(self, schedule: CommercialReportSchedule, *, reference: datetime) -> datetime:
        ref = reference.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
        if schedule.frequency == "weekly":
            day = 0 if schedule.day_of_week is None else max(0, min(6, schedule.day_of_week))
            days_ahead = (day - ref.weekday()) % 7
            candidate = (ref + timedelta(days=days_ahead)).replace(hour=schedule.hour_utc)
            if candidate <= reference.astimezone(timezone.utc):
                candidate += timedelta(days=7)
            return candidate
        day = 1 if schedule.day_of_month is None else max(1, min(28, schedule.day_of_month))
        candidate = ref.replace(day=day, hour=schedule.hour_utc)
        if candidate <= reference.astimezone(timezone.utc):
            year = candidate.year + (1 if candidate.month == 12 else 0)
            month = 1 if candidate.month == 12 else candidate.month + 1
            candidate = candidate.replace(year=year, month=month, day=day)
        return candidate

    async def set_schedule_enabled(self, schedule_id: uuid.UUID, enabled: bool) -> CommercialReportSchedule:
        schedule = await self.get_schedule(schedule_id)
        schedule.enabled = enabled
        schedule.next_run_at = self.compute_next_run_at(schedule, reference=_utc_now()) if enabled else None
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def run_schedule_now(self, schedule_id: uuid.UUID) -> dict[str, Any]:
        schedule = await self.get_schedule(schedule_id)
        self.settings = get_settings()
        filters = schedule.filters_json or {}
        report = await self.build_executive_report_data(
            hours=int(filters.get("hours", 24)),
            date_from=_parse_datetime(filters.get("date_from")),
            date_to=_parse_datetime(filters.get("date_to")),
            client_id=_parse_uuid(filters.get("client_id")),
            provider=filters.get("provider"),
            model=filters.get("model"),
        )
        result = await self._deliver_report(
            schedule_id=schedule.id,
            schedule_name=schedule.name,
            recipients=self._parse_recipients(schedule.recipients_json),
            report_format=schedule.format,
            report=report,
            delivery_mode=self._resolve_manual_delivery_mode(),
        )
        now = _utc_now()
        schedule.last_run_at = now
        schedule.next_run_at = self.compute_next_run_at(schedule, reference=now) if schedule.enabled else None
        await self.db.commit()
        return {
            "schedule_id": str(schedule.id),
            "status": result["status"],
            "email_mode": result["email_mode"],
            "generated_at_utc": now.isoformat(),
            "recipients": result["recipients"],
            "report_format": result["report_format"],
            "preview_html": result["preview_html"],
            "report": result.get("report"),
        }

    async def send_test_email(self, schedule_id: uuid.UUID) -> dict[str, Any]:
        schedule = await self.get_schedule(schedule_id)
        self.settings = get_settings()
        report = await self.build_executive_report_data(hours=1)
        recipients = self._parse_recipients(schedule.recipients_json)
        try:
            validate_recipient_allowlist(recipients, settings=self.settings)
        except AllowlistError as exc:
            delivery = await self._create_delivery_log(
                schedule_id=schedule.id,
                report_format="html",
                recipients=recipients,
                delivery_mode="dry_run" if self.settings.commercial_report_email_mode == "dry_run" else self._resolve_manual_delivery_mode(),
                delivery_status="blocked",
                subject=f"Commercial Executive Report - {schedule.name} Test",
                attachment_names=["executive-report.html"],
                error_message=str(exc),
            )
            await self.db.commit()
            return {
                "schedule_id": str(schedule.id),
                "status": "blocked",
                "email_mode": self.settings.commercial_report_email_mode,
                "recipients": recipients,
                "report_format": "html",
                "delivery_id": str(delivery.id),
            }
        result = await self._deliver_report(
            schedule_id=schedule.id,
            schedule_name=f"{schedule.name} Test",
            recipients=recipients,
            report_format="html",
            report=report,
            delivery_mode=self._resolve_manual_delivery_mode(),
        )
        await self.db.commit()
        status = "blocked" if result["status"] == "email_disabled" else result["status"]
        return {
            "schedule_id": str(schedule.id),
            "status": status,
            "email_mode": result["email_mode"],
            "recipients": result["recipients"],
            "report_format": "html",
            "delivery_id": result.get("delivery_id"),
        }

    async def list_delivery_logs(
        self,
        *,
        status: str | None = None,
        recipient: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        self.settings = get_settings()
        stmt = select(CommercialReportDeliveryLog)
        if status:
            stmt = stmt.where(CommercialReportDeliveryLog.delivery_status == status)
        if recipient:
            stmt = stmt.where(
                func.lower(cast(CommercialReportDeliveryLog.recipients_json, String)).like(f"%{recipient.lower()}%")
            )
        if date_from:
            stmt = stmt.where(CommercialReportDeliveryLog.created_at >= date_from)
        if date_to:
            stmt = stmt.where(CommercialReportDeliveryLog.created_at < date_to)
        stmt = stmt.order_by(CommercialReportDeliveryLog.created_at.desc()).limit(limit)
        deliveries = list((await self.db.execute(stmt)).scalars().all())

        counts_stmt = select(
            func.count(CommercialReportDeliveryLog.id).label("total"),
            func.sum(case((CommercialReportDeliveryLog.delivery_status == "sent", 1), else_=0)).label("sent"),
            func.sum(case((CommercialReportDeliveryLog.delivery_status == "dry_run", 1), else_=0)).label("dry_run"),
            func.sum(case((CommercialReportDeliveryLog.delivery_status == "blocked", 1), else_=0)).label("blocked"),
            func.sum(case((CommercialReportDeliveryLog.delivery_status == "failed", 1), else_=0)).label("failed"),
            func.sum(case((CommercialReportDeliveryLog.retries > 0, 1), else_=0)).label("retries"),
            func.sum(case((CommercialReportDeliveryLog.error_message.like("auth_failure:%"), 1), else_=0)).label("auth_failures"),
            func.sum(case((CommercialReportDeliveryLog.error_message.like("tls_failure:%"), 1), else_=0)).label("tls_failures"),
            func.sum(case((CommercialReportDeliveryLog.error_message.like("blocked_by_security:%"), 1), else_=0)).label("blocked_by_security"),
            func.sum(case((CommercialReportDeliveryLog.error_message.like("blocked_by_allowlist:%"), 1), else_=0)).label("blocked_by_allowlist"),
        )
        counts = (await self.db.execute(counts_stmt)).one()
        return {
            "smtp_mode": self.settings.commercial_report_email_mode,
            "smtp_enabled": self.settings.commercial_report_email_enabled,
            "send_real_email": self.settings.commercial_report_send_real_email,
            "allowlist_configured": bool(self.settings.commercial_report_email_allowlist.strip()),
            "max_recipients": self.settings.commercial_report_email_max_recipients,
            "deliveries": deliveries,
            "counts": {
                "total": int(counts.total or 0),
                "sent": int(counts.sent or 0),
                "dry_run": int(counts.dry_run or 0),
                "blocked": int(counts.blocked or 0),
                "failed": int(counts.failed or 0),
                "retries": int(counts.retries or 0),
                "auth_failures": int(counts.auth_failures or 0),
                "tls_failures": int(counts.tls_failures or 0),
                "blocked_by_security": int(counts.blocked_by_security or 0),
                "blocked_by_allowlist": int(counts.blocked_by_allowlist or 0),
            },
        }

    async def run_due_schedules_once(self) -> list[dict[str, Any]]:
        now = _utc_now()
        self.settings = get_settings()
        stmt = select(CommercialReportSchedule).where(
            CommercialReportSchedule.enabled.is_(True),
            CommercialReportSchedule.next_run_at.is_not(None),
            CommercialReportSchedule.next_run_at <= now,
        )
        schedules = list((await self.db.execute(stmt)).scalars().all())
        results = []
        for schedule in schedules:
            filters = schedule.filters_json or {}
            report = await self.build_executive_report_data(
                hours=int(filters.get("hours", 24)),
                date_from=_parse_datetime(filters.get("date_from")),
                date_to=_parse_datetime(filters.get("date_to")),
                client_id=_parse_uuid(filters.get("client_id")),
                provider=filters.get("provider"),
                model=filters.get("model"),
            )
            result = await self._deliver_report(
                schedule_id=schedule.id,
                schedule_name=schedule.name,
                recipients=self._parse_recipients(schedule.recipients_json),
                report_format=schedule.format,
                report=report,
                delivery_mode=self._resolve_automatic_delivery_mode(),
            )
            schedule.last_run_at = now
            schedule.next_run_at = self.compute_next_run_at(schedule, reference=now) if schedule.enabled else None
            results.append(result)
            logger.info("commercial report schedule evaluated", extra={"extra_data": result})
        await self.db.commit()
        return results


def _parse_uuid(value: Any) -> uuid.UUID | None:
    if not value:
        return None
    return uuid.UUID(str(value))


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
