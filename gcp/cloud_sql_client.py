import logging
from typing import Any, Iterator, Optional
import contextlib

logger = logging.getLogger(__name__)

try:
    import sqlalchemy
    from sqlalchemy import text
except ImportError:
    sqlalchemy = None  # type: ignore


class CloudSQLClient:
    def __init__(self, connection_name: str, db_name: str,
                 user: str, password: str,
                 use_public_ip: bool = False) -> None:
        self.connection_name = connection_name
        self.db_name         = db_name
        self.user            = user
        self._password       = password
        self.use_public_ip   = use_public_ip
        self._engine = None
        logger.debug("CloudSQL client for %s/%s", connection_name, db_name)

    def _get_engine(self):
        if self._engine is not None:
            return self._engine
        if sqlalchemy is None:
            raise ImportError("sqlalchemy is not installed")
        try:
            from google.cloud.sql.connector import Connector
            connector = Connector()

            def getconn():
                return connector.connect(
                    self.connection_name, "pg8000",
                    user=self.user, password=self._password,
                    db=self.db_name, ip_type="PUBLIC" if self.use_public_ip else "PRIVATE",
                )

            self._engine = sqlalchemy.create_engine(
                "postgresql+pg8000://", creator=getconn,
                pool_size=5, max_overflow=2, pool_timeout=30,
            )
        except ImportError:
            url = (f"postgresql+pg8000://{self.user}:{self._password}"
                   f"@localhost/{self.db_name}")
            self._engine = sqlalchemy.create_engine(url)
        return self._engine

    @contextlib.contextmanager
    def connection(self):
        engine = self._get_engine()
        with engine.connect() as conn:
            yield conn

    def execute(self, sql: str, params: Optional[dict] = None) -> int:
        with self.connection() as conn:
            result = conn.execute(text(sql), params or {})
            conn.commit()
            return result.rowcount

    def fetch_all(self, sql: str,
                  params: Optional[dict] = None) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(text(sql), params or {}).fetchall()
            return [dict(row._mapping) for row in rows]

    def fetch_one(self, sql: str,
                  params: Optional[dict] = None) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(text(sql), params or {}).fetchone()
            return dict(row._mapping) if row else None

    def table_exists(self, schema: str, table: str) -> bool:
        result = self.fetch_one(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = :table",
            {"schema": schema, "table": table},
        )
        return result is not None

    def run_migration(self, migration_sql: str) -> None:
        logger.info("Running migration (%d chars)", len(migration_sql))
        with self.connection() as conn:
            for statement in migration_sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))
            conn.commit()
        logger.info("Migration complete")
