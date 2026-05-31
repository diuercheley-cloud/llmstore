import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.services.notifications.pagerduty_webhook import AlertWebhookService, PagerDutyEvent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/alerts/grafana-webhook")
async def grafana_alert_webhook(request: Request):
    """
    Receives Grafana alert webhooks and forwards them to PagerDuty/OpsGenie.
    Grafana Alerting → this endpoint → PagerDuty/OpsGenie.
    """
    settings = get_settings()
    if not settings.pagerduty_routing_key and not settings.opsgenie_api_key:
        raise HTTPException(status_code=501, detail="No alerting backends configured")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    alerts = body.get("alerts", [])
    if not alerts and body.get("state"):
        alerts = [body]

    svc = AlertWebhookService()
    results = []
    for alert in alerts:
        status = alert.get("status", "firing")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        summary = annotations.get("summary") or annotations.get("message") or labels.get("alertname", "Grafana Alert")
        severity = labels.get("severity", "warning")

        event = PagerDutyEvent(
            summary=summary,
            source=f"grafana/{labels.get('grafana_folder', 'unknown')}",
            severity=severity,
            event_action="resolve" if status == "resolved" else "trigger",
            dedup_key=labels.get("alertname"),
            component=labels.get("component", "agent-runtime"),
            group=labels.get("group", "monitoring"),
            custom_details={
                "grafana_url": annotations.get("grafana_url", ""),
                "runbook_url": annotations.get("runbook_url", ""),
                "description": annotations.get("description", ""),
                "values": alert.get("values", {}),
                "labels": labels,
            },
        )
        result = await svc.send_alert(event)
        results.append({"alert": labels.get("alertname"), "result": result})

    await svc.close()
    return {"received": len(alerts), "forwarded": len(results), "results": results}


@router.post("/alerts/test-pagerduty")
async def test_pagerduty_alert():
    settings = get_settings()
    if not settings.pagerduty_routing_key:
        raise HTTPException(status_code=501, detail="PagerDuty not configured")

    svc = AlertWebhookService()
    event = PagerDutyEvent(
        summary="[TEST] LLM Inference Stack — connectivity test",
        source="api-test",
        severity="info",
        dedup_key="test-alert-llm-inference-stack",
        group="test",
        custom_details={"test": True, "timestamp": None},
    )
    result = await svc.send_alert(event)
    await svc.close()
    return {"message": "Test alert sent", "result": result}


@router.post("/alerts/resolve")
async def resolve_alert(dedup_key: str, summary: str = "Resolved via API"):
    settings = get_settings()
    if not settings.pagerduty_routing_key:
        raise HTTPException(status_code=501, detail="PagerDuty not configured")

    svc = AlertWebhookService()
    result = await svc.resolve_alert(dedup_key, summary)
    await svc.close()
    return {"resolved": True, "result": result}
