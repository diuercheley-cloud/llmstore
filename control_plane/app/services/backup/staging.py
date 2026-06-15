import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

from app.db.base import Base
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from .errors import RestoreStagingError

logger = logging.getLogger(__name__)


class RestoreStagingService:
    def __init__(self, db: AsyncSession, db_url: str):
        self.db = db
        self.db_url = db_url

    async def setup_staging_db(self, staging_dbname: str) -> tuple[str, str | None, Path | None]:
        if self.db_url.startswith("postgresql") or self.db_url.startswith("postgres"):
            try:
                staging_db_url = await self._create_postgres_staging_db(staging_dbname)
                return staging_db_url, staging_dbname, None
            except Exception as e:
                raise RestoreStagingError(f"Failed to create staging PG database: {e}")
        else:
            sqlite_temp_dir = tempfile.mkdtemp(prefix="sqlite-staging-")
            sqlite_staging_file = Path(sqlite_temp_dir) / "staging.db"
            staging_db_url = f"sqlite+aiosqlite:///{sqlite_staging_file}"
            return staging_db_url, None, sqlite_staging_file

    async def _create_postgres_staging_db(self, staging_dbname: str) -> str:
        from urllib.parse import quote, urlparse

        def build_url(db_name):
            clean_url = self.db_url.replace("postgresql+asyncpg://", "postgresql://")
            parsed = urlparse(clean_url)
            username = parsed.username or ""
            password = parsed.password or ""
            credentials = quote(username, safe="")
            if password:
                credentials = f"{credentials}:{quote(password, safe='')}"
            host = parsed.hostname or "localhost"
            port = parsed.port or 5432
            auth = f"{credentials}@" if credentials else ""
            return f"postgresql+asyncpg://{auth}{host}:{port}/{db_name}"

        admin_url = build_url("postgres")
        admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
        async with admin_engine.connect() as conn:
            await conn.execute(text(f"CREATE DATABASE {staging_dbname}"))
        await admin_engine.dispose()
        return build_url(staging_dbname)

    async def cleanup_staging(
        self, staging_dbname: str | None, sqlite_staging_file: Path | None
    ) -> None:
        if sqlite_staging_file and sqlite_staging_file.parent.exists():
            shutil.rmtree(sqlite_staging_file.parent, ignore_errors=True)
        elif staging_dbname and (
            self.db_url.startswith("postgresql") or self.db_url.startswith("postgres")
        ):
            try:
                # Need build_url again or make it a helper
                from urllib.parse import quote, urlparse

                def build_url(db_name):
                    clean_url = self.db_url.replace("postgresql+asyncpg://", "postgresql://")
                    parsed = urlparse(clean_url)
                    username = parsed.username or ""
                    password = parsed.password or ""
                    credentials = quote(username, safe="")
                    if password:
                        credentials = f"{credentials}:{quote(password, safe='')}"
                    host = parsed.hostname or "localhost"
                    port = parsed.port or 5432
                    auth = f"{credentials}@" if credentials else ""
                    return f"postgresql+asyncpg://{auth}{host}:{port}/{db_name}"

                admin_url = build_url("postgres")
                admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
                async with admin_engine.connect() as conn:
                    await conn.execute(
                        text(f"""
                        SELECT pg_terminate_backend(pg_stat_activity.pid)
                        FROM pg_stat_activity
                        WHERE pg_stat_activity.datname = '{staging_dbname}'
                          AND pid <> pg_backend_pid()
                    """)
                    )
                    await conn.execute(text(f"DROP DATABASE IF EXISTS {staging_dbname}"))
                await admin_engine.dispose()
            except Exception as e:
                logger.error(f"Failed to drop staging postgres database: {e}")

    async def validate_staging_db(self, staging_engine, scope: str) -> dict[str, Any]:
        report = {
            "valid": True,
            "errors": [],
            "alembic_head": "none",
            "verified_tables": [],
            "missing_tables": [],
        }
        async with staging_engine.connect() as conn:
            # 1. Check alembic head
            try:
                result = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                row = result.fetchone()
                report["alembic_head"] = row[0] if row else "none"
            except Exception:
                pass

            # 2. Check schema
            def _inspect_tables(sync_conn):
                inspector = inspect(sync_conn)
                return inspector.get_table_names()

            existing_tables = await conn.run_sync(_inspect_tables)
            expected_tables = list(Base.metadata.tables.keys())

            if scope == "full":
                missing = [t for t in expected_tables if t not in existing_tables]
                report["verified_tables"] = [t for t in expected_tables if t in existing_tables]
                report["missing_tables"] = missing
                if missing:
                    report["errors"].append(f"Missing expected database tables: {missing}")
                    report["valid"] = False
            else:
                logical_tables = ["agent_definitions", "agent_memory_items"]
                missing = [t for t in logical_tables if t not in existing_tables]
                report["verified_tables"] = [t for t in logical_tables if t in existing_tables]
                report["missing_tables"] = missing
                if missing:
                    report["errors"].append(f"Missing logical agent tables: {missing}")
                    report["valid"] = False
        return report
