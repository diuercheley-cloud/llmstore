import logging
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.web_search import AgentWebSearchPolicyEvent, AgentWebSearchQuery
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

BANNED_WORDS = {"banned-word", "malware-download", "exploit-tool"}
PROMPT_INJECTION_KEYWORDS = {
    "ignore previous instructions",
    "ignore system prompt",
    "ignore the system prompt",
    "ignore instructions",
    "system command injection",
    "ignore all instructions",
}

DEFAULT_ALLOWLIST = {
    "github.com",
    "wikipedia.org",
    "weather-mock.local",
    "nws-mock.internal",
    "search-results.local",
    "blog.llmstack.internal",
    "security-exploit.local",
    "localhost",
    "127.0.0.1",
}

DEFAULT_BLOCKLIST = {
    "dangerous-site.com",
    "malicious.org",
    "malware.com",
}


class SearchPolicyService:
    @property
    def settings(self):
        return get_settings()

    def _get_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or parsed.netloc or ""
            return hostname.lower()
        except Exception:
            return ""

    async def check_search_allowed(
        self,
        db: AsyncSession,
        tenant_id: str,
        agent_id: uuid.UUID | None,
        query: str,
    ) -> None:
        # 1. Feature flag verification
        if not self.settings.agent_web_search_enabled:
            await self.log_policy_event(
                db,
                tenant_id,
                agent_id,
                query,
                "disabled",
                {"reason": "AGENT_WEB_SEARCH_ENABLED feature flag is false"},
            )
            raise HTTPException(
                status_code=403,
                detail="Agent web search capability is disabled on this server.",
            )

        # 2. Query content safety verification
        query_lower = query.lower()
        for word in BANNED_WORDS:
            if word in query_lower:
                await self.log_policy_event(
                    db,
                    tenant_id,
                    agent_id,
                    query,
                    "content_safety_blocked",
                    {"reason": f"Query contains banned word: {word}"},
                )
                raise HTTPException(
                    status_code=400,
                    detail="Query rejected due to content safety policy.",
                )

        # 3. Rate Limit enforcement (per tenant / agent)
        # Limit to 5 requests per minute
        one_minute_ago = utc_now() - timedelta(minutes=1)
        stmt = select(func.count(AgentWebSearchQuery.id)).where(
            AgentWebSearchQuery.tenant_id == tenant_id,
            AgentWebSearchQuery.created_at >= one_minute_ago,
        )
        res = await db.execute(stmt)
        count = res.scalar() or 0
        if count >= 5:
            await self.log_policy_event(
                db,
                tenant_id,
                agent_id,
                query,
                "rate_limit_exceeded",
                {"count_last_minute": count, "limit": 5},
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded for web search queries. Max 5 per minute.",
            )

    async def filter_and_sanitize_results(
        self,
        db: AsyncSession,
        tenant_id: str,
        agent_id: uuid.UUID | None,
        query: str,
        results: list[dict],
    ) -> list[dict]:
        filtered_results = []
        for r in results:
            url = r.get("url", "")
            domain = self._get_domain(url)

            # Check blocklist
            if domain in DEFAULT_BLOCKLIST:
                logger.info(f"Filtering result url {url} due to blocklist domain.")
                continue

            # Check allowlist
            if self.settings.agent_web_search_allowlist_enabled:
                allowed = False
                for allowed_domain in DEFAULT_ALLOWLIST:
                    if domain == allowed_domain or domain.endswith(
                        "." + allowed_domain
                    ):
                        allowed = True
                        break
                if not allowed:
                    logger.info(
                        f"Filtering result url {url} because it is not in the allowlist."
                    )
                    continue

            # Sanitization of prompt injection in title or snippet
            sanitized = False
            title = r.get("title", "")
            snippet = r.get("snippet", "")

            # Check prompt injection patterns in snippet/title
            for pattern in PROMPT_INJECTION_KEYWORDS:
                if pattern in title.lower() or pattern in snippet.lower():
                    sanitized = True
                    break

            if sanitized:
                # Sanitize content
                r["title"] = "[Redacted: Prompt Injection Attempt]"
                r["snippet"] = (
                    "[Content redacted by safety engine to prevent prompt injection]"
                )
                await self.log_policy_event(
                    db,
                    tenant_id,
                    agent_id,
                    query,
                    "prompt_injection_sanitized",
                    {"url": url, "original_title": title, "original_snippet": snippet},
                )

            filtered_results.append(r)

        return filtered_results

    async def log_policy_event(
        self,
        db: AsyncSession,
        tenant_id: str,
        agent_id: uuid.UUID | None,
        query: str | None,
        event_type: str,
        details: dict,
    ) -> None:
        event = AgentWebSearchPolicyEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            agent_id=agent_id,
            query=query,
            event_type=event_type,
            details=details,
            created_at=utc_now(),
        )
        db.add(event)
        await db.commit()
