import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


SEVERITY_MAP = {
    "critical": "critical",
    "error": "error",
    "warning": "warning",
    "info": "info",
}


@dataclass
class PagerDutyEvent:
    summary: str
    source: str = "llm-inference-stack"
    severity: str = "warning"
    event_action: str = "trigger"
    dedup_key: Optional[str] = None
    component: Optional[str] = None
    group: Optional[str] = None
    cls: Optional[str] = None
    custom_details: Dict[str, Any] = field(default_factory=dict)
    links: List[Dict[str, str]] = field(default_factory=list)

    def to_payload(self) -> Dict:
        payload = {
            "routing_key": "",
            "event_action": self.event_action,
            "payload": {
                "summary": self.summary,
                "source": self.source,
                "severity": SEVERITY_MAP.get(self.severity, "warning"),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "component": self.component or "platform",
                "group": self.group or "agent-monitoring",
                "class": self.cls or "observability",
                "custom_details": self.custom_details,
            },
            "links": self.links,
        }
        if self.dedup_key:
            payload["dedup_key"] = self.dedup_key
        if self.event_action == "acknowledge":
            payload["event_action"] = "acknowledge"
        return payload


@dataclass
class OpsGenieEvent:
    message: str
    alias: Optional[str] = None
    description: Optional[str] = None
    responders: List[Dict[str, str]] = field(default_factory=list)
    priority: str = "P3"
    source: str = "llm-inference-stack"
    tags: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    entity: Optional[str] = None

    def to_payload(self) -> Dict:
        return {
            "message": self.message,
            "alias": self.alias,
            "description": self.description,
            "responders": self.responders,
            "priority": self.priority,
            "source": self.source,
            "tags": self.tags,
            "details": self.details,
            "entity": self.entity,
        }


class AlertWebhookService:
    """
    Sends real-time alerts to PagerDuty and/or OpsGenie.
    Configured via env vars:
      PAGERDUTY_ROUTING_KEY
      OPSGENIE_API_KEY
      OPSGENIE_API_URL
    """

    def __init__(self):
        self.settings = get_settings()
        self.pd_routing_key = self.settings.pagerduty_routing_key or ""
        self.og_api_key = self.settings.opsgenie_api_key or ""
        self.og_api_url = self.settings.opsgenie_api_url or "https://api.opsgenie.com/v2/alerts"
        self._http = httpx.AsyncClient(timeout=10.0)

    async def send_alert(self, event: PagerDutyEvent):
        results = {}
        if self.pd_routing_key:
            results["pagerduty"] = await self._send_pagerduty(event)
        if self.og_api_key:
            og_event = OpsGenieEvent(
                message=event.summary,
                description=json.dumps(event.custom_details, indent=2),
                priority=self._severity_to_priority(event.severity),
                tags=[event.group or "agent", event.component or "platform"],
                details=event.custom_details,
                entity=event.source,
            )
            results["opsgenie"] = await self._send_opsgenie(og_event)
        return results

    async def resolve_alert(self, dedup_key: str, summary: str = "Resolved"):
        results = {}
        if self.pd_routing_key:
            resolve_event = PagerDutyEvent(
                summary=summary,
                event_action="resolve",
                dedup_key=dedup_key,
            )
            results["pagerduty"] = await self._send_pagerduty(resolve_event)
        return results

    async def acknowledge_alert(self, dedup_key: str):
        results = {}
        if self.pd_routing_key:
            ack_event = PagerDutyEvent(
                summary="Acknowledged",
                event_action="acknowledge",
                dedup_key=dedup_key,
            )
            results["pagerduty"] = await self._send_pagerduty(ack_event)
        return results

    async def _send_pagerduty(self, event: PagerDutyEvent) -> Dict:
        payload = event.to_payload()
        payload["routing_key"] = self.pd_routing_key
        try:
            resp = await self._http.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            body = resp.json()
            if resp.is_success:
                logger.info(f"PagerDuty alert sent: {body.get('dedup_key', 'unknown')}")
            else:
                logger.error(f"PagerDuty error {resp.status_code}: {body}")
            return {"status": resp.status_code, "response": body}
        except Exception as e:
            logger.error(f"PagerDuty request failed: {e}")
            return {"error": str(e)}

    async def _send_opsgenie(self, event: OpsGenieEvent) -> Dict:
        payload = event.to_payload()
        try:
            resp = await self._http.post(
                self.og_api_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"GenieKey {self.og_api_key}",
                },
            )
            body = resp.json()
            if resp.is_success:
                logger.info(f"OpsGenie alert sent: {body.get('id', 'unknown')}")
            else:
                logger.error(f"OpsGenie error {resp.status_code}: {body}")
            return {"status": resp.status_code, "response": body}
        except Exception as e:
            logger.error(f"OpsGenie request failed: {e}")
            return {"error": str(e)}

    def _severity_to_priority(self, severity: str) -> str:
        mapping = {
            "critical": "P1",
            "error": "P2",
            "warning": "P3",
            "info": "P4",
        }
        return mapping.get(severity, "P3")

    async def close(self):
        await self._http.aclose()
