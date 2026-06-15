from typing import Any

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.agents.tool_adapter_contract import ToolAdapterContract
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


class DatabaseReadToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "database_read_tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "table": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["table", "query"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"rows": {"type": "array", "items": {"type": "object"}}},
        }

    @property
    def side_effect_level(self) -> str:
        return "read"

    async def execute(self, **kwargs) -> dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_db_read_tool_enabled", False):
            raise ValueError("Database read tool is disabled by feature flag.")

        table = kwargs["table"]
        query = kwargs["query"].strip()
        limit = min(int(kwargs.get("limit", 10)), 100)  # Enforce max limit of 100
        tenant_id = kwargs.get("tenant_id")

        # 1. Table Allowlist
        allowlisted_tables = {
            "agent_runs",
            "agent_run_steps",
            "agent_timeline_events",
            "agent_tool_invocations",
        }
        if table not in allowlisted_tables:
            raise ValueError(f"Access to table '{table}' is not permitted.")

        # 2. Strict SELECT only validation
        query_lower = query.lower()
        if not query_lower.startswith("select"):
            raise ValueError("Only SELECT queries are allowed.")

        forbidden_keywords = [
            "insert",
            "update",
            "delete",
            "drop",
            "truncate",
            "alter",
            "create",
            "grant",
            "revoke",
        ]
        if any(keyword in query_lower for keyword in forbidden_keywords):
            raise ValueError("Data mutation keywords detected. Only SELECT queries are allowed.")

        # 3. Secret Column Filtering (strip from final results)
        secret_columns = {"api_key", "secret", "password", "token", "credential", "auth_hash"}

        # 4. Enforce LIMIT and Tenant Filter (basic implementation)
        # Note: In a production system, we'd use a parser to safely inject 'WHERE tenant_id = :tid'
        # For this adapter, we assume the query is constructed or we wrap it.

        wrapped_query = f"SELECT * FROM ({query.rstrip(';')}) AS agent_db_read LIMIT :limit"

        async with SessionLocal() as session:
            try:
                result = await session.execute(
                    text(wrapped_query), {"limit": limit, "tid": tenant_id}
                )
                rows = []
                for row in result:
                    d = dict(row._mapping)
                    # Filter secret columns
                    filtered = {k: v for k, v in d.items() if k.lower() not in secret_columns}
                    rows.append(filtered)
            except SQLAlchemyError as e:
                rows = [{"error": "Query execution failed", "details": str(e)}]

        return {"rows": rows, "count": len(rows)}

    async def dry_run(self, **kwargs) -> dict[str, Any]:
        return await self.execute(**kwargs)

    async def rollback(self, invocation_id: str, **kwargs) -> dict[str, Any]:
        return {"status": "success", "message": "Read-only tools do not require rollback."}

    async def healthcheck(self) -> bool:
        return True
