"""
Owner: agent-platform
Status: beta
"""
import logging
import uuid
from typing import Any, Dict, List

from app.core.time import utc_now
from app.models.agents.agents import AgentTraceLink, AgentTraceSpan
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class AgentTraceCorrelationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def link_traces(
        self,
        run_id: uuid.UUID,
        trace_id: str,
        linked_trace_id: str,
        reason: str
    ) -> AgentTraceLink:
        link = AgentTraceLink(
            run_id=run_id,
            trace_id=trace_id,
            linked_trace_id=linked_trace_id,
            link_reason=reason,
            created_at=utc_now()
        )
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def get_run_correlation(self, run_id: uuid.UUID) -> Dict[str, Any]:
        """Builds a tree of correlated traces/spans for a run."""
        # 1. Fetch direct spans for run
        res_spans = await self.db.execute(
            select(AgentTraceSpan).where(AgentTraceSpan.run_id == run_id)
        )
        spans = res_spans.scalars().all()

        # 2. Fetch linked traces (e.g. from handoffs)
        res_links = await self.db.execute(
            select(AgentTraceLink).where(AgentTraceLink.run_id == run_id)
        )
        links = res_links.scalars().all()

        # 3. Assemble correlation view
        return {
            "run_id": str(run_id),
            "spans_count": len(spans),
            "links": [
                {
                    "trace_id": l.trace_id,
                    "linked_trace_id": l.linked_trace_id,
                    "reason": l.link_reason
                } for l in links
            ],
            "trace_hierarchy": self._build_span_tree(spans)
        }

    def _build_span_tree(self, spans: List[AgentTraceSpan]) -> List[Dict[str, Any]]:
        # Simple tree construction logic
        span_map = {str(s.span_id): s for s in spans}
        roots = []
        for s in spans:
            if not s.parent_span_id or str(s.parent_span_id) not in span_map:
                roots.append(self._format_span(s, spans))
        return roots

    def _format_span(self, span: AgentTraceSpan, all_spans: List[AgentTraceSpan]) -> Dict[str, Any]:
        children = [s for s in all_spans if s.parent_span_id == span.span_id]
        return {
            "id": str(span.id),
            "name": span.name,
            "type": span.span_type,
            "status": span.status,
            "start_time": span.start_time.isoformat(),
            "end_time": span.end_time.isoformat() if span.end_time else None,
            "children": [self._format_span(c, all_spans) for c in children]
        }
