from typing import Any, Dict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.services.agents.tool_adapter_contract import ToolAdapterContract
from app.core.config import get_settings
from app.db.session import SessionLocal


class DatabaseReadToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "database_read_tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "table": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["table", "query"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {"type": "object"}
                }
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "read"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_db_read_tool_enabled", False):
            raise ValueError("Database read tool is disabled by feature flag.")

        query = kwargs["query"].strip()
        limit = int(kwargs.get("limit", 10))
        # Basic SQL injection / mutation prevention
        query_lower = query.lower()
        if not query_lower.startswith("select"):
            raise ValueError("Only SELECT queries are allowed in database_read_tool.")
        if any(keyword in query_lower for keyword in ["insert", "update", "delete", "drop", "truncate", "alter"]):
            raise ValueError("Only SELECT queries are allowed in database_read_tool.")
        if ";" in query.rstrip(";"):
            raise ValueError("Multiple SQL statements are not allowed in database_read_tool.")

        limited_query = f"SELECT * FROM ({query.rstrip(';')}) AS agent_db_read LIMIT :limit"
        async with SessionLocal() as session:
            try:
                result = await session.execute(text(limited_query), {"limit": limit})
                rows = [dict(row._mapping) for row in result]
            except SQLAlchemyError:
                rows = []
        return {"rows": rows}

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return await self.execute(**kwargs)

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "Read-only tools do not require rollback."}

    async def healthcheck(self) -> bool:
        return True
