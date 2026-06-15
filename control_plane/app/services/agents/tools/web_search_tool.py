import uuid
from typing import Any

from app.db.session import SessionLocal
from app.services.agents.tool_adapter_contract import ToolAdapterContract
from app.services.agents.web_search.http_search_provider import HttpSearchProvider
from app.services.agents.web_search.mock_search_provider import MockSearchProvider
from app.services.agents.web_search.search_audit import SearchAuditService
from app.services.agents.web_search.search_cache import SearchCacheService
from app.services.agents.web_search.search_policy import SearchPolicyService


class WebSearchToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query term."},
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of search results to return.",
                    "default": 5,
                },
                "provider": {
                    "type": "string",
                    "description": "Provider backend to use (mock or http).",
                    "default": "mock",
                },
            },
            "required": ["query"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query_hash": {"type": "string"},
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "snippet": {"type": "string"},
                            "url": {"type": "string"},
                            "confidence": {"type": "number"},
                            "provider": {"type": "string"},
                            "retrieved_at": {"type": "string"},
                        },
                    },
                },
                "citation": {"type": "string"},
                "audit_event_id": {"type": "string"},
                "result_ids": {"type": "array", "items": {"type": "string"}},
            },
        }

    @property
    def side_effect_level(self) -> str:
        return "external_read"

    def to_registry_dict(self) -> dict[str, Any]:
        data = super().to_registry_dict()
        data["risk_level"] = "medium"
        data["category"] = "external_api"
        data["data_boundary"] = "internet"
        return data

    async def execute(self, **kwargs) -> dict[str, Any]:
        query = kwargs["query"]
        limit = int(kwargs.get("limit", 5))
        provider_name = kwargs.get("provider", "mock")
        tenant_id = kwargs.get("tenant_id", "default")

        agent_id_raw = kwargs.get("agent_id")
        agent_id = uuid.UUID(str(agent_id_raw)) if agent_id_raw else None

        run_id_raw = kwargs.get("run_id")
        run_id = uuid.UUID(str(run_id_raw)) if run_id_raw else None

        db_override = kwargs.get("db")
        if db_override is not None:
            return await self._execute_with_db(
                db_override, query, limit, provider_name, tenant_id, agent_id, run_id
            )
        else:
            async with SessionLocal() as db:
                return await self._execute_with_db(
                    db, query, limit, provider_name, tenant_id, agent_id, run_id
                )

    async def _execute_with_db(
        self, db, query, limit, provider_name, tenant_id, agent_id, run_id
    ) -> dict[str, Any]:
        policy_service = SearchPolicyService()
        cache_service = SearchCacheService()
        audit_service = SearchAuditService()

        # 1. Enforce query policy limits/checks
        await policy_service.check_search_allowed(db, tenant_id, agent_id, query)

        # 2. Check Cache
        query_hash = audit_service.get_query_hash(query)
        cached_results = await cache_service.get_cached_results(db, query_hash)

        if cached_results is not None:
            # Cache Hit! Re-filter/sanitize cached results
            results = await policy_service.filter_and_sanitize_results(
                db, tenant_id, agent_id, query, cached_results
            )
            audit_record = await audit_service.log_search(
                db,
                tenant_id,
                agent_id,
                run_id,
                query,
                f"cache:{provider_name}",
                results,
            )
        else:
            # Cache Miss!
            if provider_name == "http":
                provider = HttpSearchProvider()
            else:
                provider = MockSearchProvider()

            raw_results = await provider.search(query, limit)
            results = await policy_service.filter_and_sanitize_results(
                db, tenant_id, agent_id, query, raw_results
            )
            await cache_service.save_to_cache(db, query_hash, results)
            audit_record = await audit_service.log_search(
                db, tenant_id, agent_id, run_id, query, provider_name, results
            )

        citations = [f"{r['title']} ({r['url']})" for r in results]
        citation_str = ", ".join(citations)

        return {
            "query_hash": query_hash,
            "results": results,
            "citation": citation_str,
            "audit_event_id": str(audit_record.id),
            "result_ids": [str(r.get("id", "")) for r in results],
        }

    async def dry_run(self, **kwargs) -> dict[str, Any]:
        return await self.execute(**kwargs)

    async def rollback(self, invocation_id: str, **kwargs) -> dict[str, Any]:
        return {
            "status": "success",
            "message": "Read-only search tools do not require rollback.",
        }

    async def healthcheck(self) -> bool:
        return True
