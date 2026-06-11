import os
import subprocess
import sqlite3
import hashlib
import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

class DatabaseBackupProvider(ABC):
    def __init__(self, db: AsyncSession, db_url: str):
        self.db = db
        self.db_url = db_url

    @abstractmethod
    async def dump_database(self, dest_file: Path) -> Dict[str, Any]:
        """
        Dumps the database to dest_file and returns metadata.
        """
        pass

    @abstractmethod
    async def restore_database(self, src_file: Path) -> None:
        """
        Restores the database from src_file.
        """
        pass

    async def get_alembic_head(self) -> str:
        try:
            result = await self.db.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            return row[0] if row else "none"
        except Exception:
            return "none"


class SQLiteBackupProvider(DatabaseBackupProvider):
    async def _dispose_engine(self) -> None:
        engine = getattr(self.db, "bind", None)
        if engine is not None and hasattr(engine, "dispose"):
            await engine.dispose()

    async def dump_database(self, dest_file: Path) -> Dict[str, Any]:
        # Perform consistent SQLite backup using backup API
        raw_conn = await self.db.connection()
        if hasattr(raw_conn, "get_raw_connection"):
            dbapi_conn = await raw_conn.get_raw_connection()
        else:
            dbapi_conn = raw_conn.connection
        if hasattr(dbapi_conn, "driver_connection"):
            dbapi_conn = dbapi_conn.driver_connection
        elif hasattr(dbapi_conn, "dbapi_connection"):
            dbapi_conn = dbapi_conn.dbapi_connection

        dest_conn = sqlite3.connect(str(dest_file))
        try:
            if hasattr(dbapi_conn, "backup") and inspect.iscoroutinefunction(dbapi_conn.backup):
                await dbapi_conn.backup(dest_conn)
            elif hasattr(dbapi_conn, "backup"):
                dbapi_conn.backup(dest_conn)
            else:
                if hasattr(dbapi_conn, "_connection"):
                    raw_sqlite = dbapi_conn._connection
                elif hasattr(dbapi_conn, "_conn"):
                    raw_sqlite = dbapi_conn._conn
                else:
                    raw_sqlite = dbapi_conn
                
                def _sync_backup(connection):
                    conn_to_use = connection.connection
                    if hasattr(conn_to_use, "dbapi_connection"):
                        conn_to_use = conn_to_use.dbapi_connection
                    if hasattr(conn_to_use, "_connection"):
                        conn_to_use = conn_to_use._connection
                    if hasattr(conn_to_use, "_conn"):
                        conn_to_use = conn_to_use._conn
                    conn_to_use.backup(dest_conn)
                await raw_conn.run_sync(_sync_backup)
        finally:
            dest_conn.close()

        # Validate dump
        if not self._validate_dump(dest_file):
            raise ValueError("SQLite backup validation failed: integrity check failed or empty file.")

        alembic_head = await self.get_alembic_head()

        return {
            "database_engine": "sqlite",
            "database_version": sqlite3.sqlite_version,
            "schema_revision": alembic_head,
            "alembic_head": alembic_head,
            "dump_format": "sqlite-binary",
        }

    async def restore_database(self, src_file: Path) -> None:
        if not self._validate_dump(src_file):
            raise ValueError("Cannot restore: SQLite backup source file is invalid or corrupted.")

        from urllib.parse import urlparse

        def _sqlite_path_from_url() -> Path | None:
            if "mode=memory" in self.db_url or "cache=shared" in self.db_url and "file:" in self.db_url:
                return None
            parsed = urlparse(self.db_url.replace("sqlite+aiosqlite:///", "sqlite:///"))
            if parsed.scheme != "sqlite":
                return None
            if not parsed.path:
                return None
            return Path(parsed.path)

        dest_path = _sqlite_path_from_url()
        if dest_path is not None:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            temp_dest = dest_path.with_suffix(dest_path.suffix + ".restore.tmp")
            if temp_dest.exists():
                temp_dest.unlink()
            dest_conn = sqlite3.connect(str(temp_dest))
            src_conn = sqlite3.connect(str(src_file))
            try:
                src_conn.backup(dest_conn)
            finally:
                src_conn.close()
                dest_conn.close()
            os.replace(temp_dest, dest_path)
            await self._dispose_engine()
            return

        raw_conn = await self.db.connection()
        if hasattr(raw_conn, "get_raw_connection"):
            dbapi_conn = await raw_conn.get_raw_connection()
        else:
            dbapi_conn = raw_conn.connection
        if hasattr(dbapi_conn, "driver_connection"):
            dbapi_conn = dbapi_conn.driver_connection
        elif hasattr(dbapi_conn, "dbapi_connection"):
            dbapi_conn = dbapi_conn.dbapi_connection

        if hasattr(dbapi_conn, "_execute") and hasattr(dbapi_conn, "_conn"):
            def perform_restore():
                src_conn = sqlite3.connect(str(src_file))
                try:
                    src_conn.backup(dbapi_conn._conn)
                finally:
                    src_conn.close()
            await dbapi_conn._execute(perform_restore)
            await self._dispose_engine()
        else:
            def _sync_restore(connection):
                conn_to_use = connection.connection
                if hasattr(conn_to_use, "dbapi_connection"):
                    conn_to_use = conn_to_use.dbapi_connection
                if hasattr(conn_to_use, "_connection"):
                    conn_to_use = conn_to_use._connection
                if hasattr(conn_to_use, "_conn"):
                    conn_to_use = conn_to_use._conn
                
                src_conn = sqlite3.connect(str(src_file))
                try:
                    src_conn.backup(conn_to_use)
                finally:
                    src_conn.close()
            await raw_conn.run_sync(_sync_restore)
            await self._dispose_engine()

    def _validate_dump(self, path: Path) -> bool:
        try:
            if not path.exists() or path.stat().st_size == 0:
                return False
            conn = sqlite3.connect(str(path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            res = cursor.fetchone()
            conn.close()
            return res and res[0] == "ok"
        except Exception:
            return False


class PostgresBackupProvider(DatabaseBackupProvider):
    def _parse_url(self) -> Dict[str, Any]:
        clean_url = self.db_url.replace("postgresql+asyncpg://", "postgresql://")
        parsed = urlparse(clean_url)
        username = parsed.username
        password = parsed.password
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        dbname = parsed.path[1:] if parsed.path else ""
        return {
            "username": username,
            "password": password,
            "host": host,
            "port": port,
            "dbname": dbname,
        }

    async def dump_database(self, dest_file: Path) -> Dict[str, Any]:
        params = self._parse_url()
        env = os.environ.copy()
        if params["password"]:
            env["PGPASSWORD"] = params["password"]

        cmd = [
            "pg_dump",
            "-h", params["host"],
            "-p", str(params["port"]),
            "-U", params["username"],
            "-F", "c",
            "-f", str(dest_file),
            params["dbname"]
        ]

        # Run pg_dump
        process = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if process.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {process.stderr}")

        # Validate dump (should start with PGDMP)
        if not self._validate_dump(dest_file):
            raise ValueError("Postgres backup validation failed: invalid format or empty file.")

        alembic_head = await self.get_alembic_head()

        # Get Postgres version
        db_version = "unknown"
        try:
            res = await self.db.execute(text("SELECT version()"))
            row = res.fetchone()
            if row:
                db_version = row[0]
        except Exception:
            pass

        return {
            "database_engine": "postgresql",
            "database_version": db_version,
            "schema_revision": alembic_head,
            "alembic_head": alembic_head,
            "dump_format": "pg_dump-custom",
        }

    async def restore_database(self, src_file: Path) -> None:
        if not self._validate_dump(src_file):
            raise ValueError("Cannot restore: Postgres backup source file is invalid or corrupted.")

        params = self._parse_url()
        env = os.environ.copy()
        if params["password"]:
            env["PGPASSWORD"] = params["password"]

        # pg_restore cmd
        cmd = [
            "pg_restore",
            "-h", params["host"],
            "-p", str(params["port"]),
            "-U", params["username"],
            "-d", params["dbname"],
            "--clean",
            "--no-owner",
            "--no-privileges",
            str(src_file)
        ]

        process = subprocess.run(cmd, env=env, capture_output=True, text=True)
        # Note: pg_restore can exit with non-zero but warning codes (e.g. if objects didn't exist to drop)
        # Usually, a returncode of 0 or 1 with ignorable warnings is fine, but if it is major failure:
        if process.returncode not in (0, 1):
            raise RuntimeError(f"pg_restore failed: {process.stderr}")

    def _validate_dump(self, path: Path) -> bool:
        try:
            if not path.exists() or path.stat().st_size == 0:
                return False
            with open(path, "rb") as f:
                header = f.read(5)
            return header == b"PGDMP"
        except Exception:
            return False
