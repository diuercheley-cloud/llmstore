# Owner: agent-platform
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from app.models.agent_sessions import AgentSessionSummary
from app.services.agents.sessions.conversation_thread_service import (
    ConversationThreadService,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"token-[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"password=[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"api_key['\"]?\s*[:=]\s*['\"][a-zA-Z0-9_\-]+", re.IGNORECASE),
    re.compile(r"secret['\"]?\s*[:=]\s*['\"][a-zA-Z0-9_\-]+", re.IGNORECASE),
]


def _redact_secrets(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def _redact_pii(text: str) -> str:
    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    phone_pattern = re.compile(r"\b\d{2,3}[\s.-]?\d{4,5}[\s.-]?\d{4}\b")
    text = email_pattern.sub("[EMAIL REDACTED]", text)
    text = phone_pattern.sub("[PHONE REDACTED]", text)
    return text


class SessionContextBuilder:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.thread_service = ConversationThreadService(db)

    async def build_context(
        self,
        session_id: uuid.UUID,
        max_messages: int = 50,
        include_summary: bool = True,
        redact_secrets: bool = True,
        redact_pii: bool = True,
        max_tokens_estimate: Optional[int] = None,
    ) -> Dict[str, Any]:
        history = await self.thread_service.build_conversation_history(
            session_id=session_id,
            max_messages=max_messages,
            include_summary=False,
        )

        if redact_secrets or redact_pii:
            for entry in history:
                if isinstance(entry.get("content"), str):
                    text = entry["content"]
                    if redact_secrets:
                        text = _redact_secrets(text)
                    if redact_pii:
                        text = _redact_pii(text)
                    entry["content"] = text

        context = {
            "session_id": str(session_id),
            "history": history,
            "message_count": len(history),
        }

        if include_summary:
            from sqlalchemy import desc
            from sqlalchemy.future import select

            stmt = (
                select(AgentSessionSummary)
                .where(AgentSessionSummary.session_id == session_id)
                .order_by(desc(AgentSessionSummary.created_at))
                .limit(1)
            )
            res = await self.db.execute(stmt)
            summary = res.scalar_one_or_none()
            if summary:
                context["summary"] = summary.summary_text
                context["summary_message_count"] = summary.message_count

        if max_tokens_estimate:
            context = self._truncate_to_token_budget(context, max_tokens_estimate)

        return context

    async def build_context_for_llm(
        self,
        session_id: uuid.UUID,
        max_messages: int = 50,
        include_summary: bool = True,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        context = await self.build_context(
            session_id=session_id,
            max_messages=max_messages,
            include_summary=include_summary,
            redact_secrets=True,
            redact_pii=True,
        )

        messages: List[Dict[str, Any]] = []

        if include_summary and context.get("summary"):
            messages.append({
                "role": "system",
                "content": f"Previous conversation summary: {context['summary']}",
            })

        for entry in context["history"]:
            messages.append({
                "role": entry["role"],
                "content": entry["content"],
            })

        return messages

    def _truncate_to_token_budget(
        self, context: Dict[str, Any], max_tokens: int
    ) -> Dict[str, Any]:
        rough_tokens = sum(
            len(str(entry.get("content", ""))) // 4
            for entry in context.get("history", [])
        )
        if rough_tokens <= max_tokens:
            return context

        budget_per_msg = max_tokens // max(len(context["history"]), 1)
        truncated = []
        for entry in context["history"]:
            content = entry.get("content", "")
            if len(content) // 4 > budget_per_msg:
                content = content[: budget_per_msg * 4] + "... [truncated]"
            truncated.append({**entry, "content": content})

        context["history"] = truncated
        context["truncated"] = True
        return context
