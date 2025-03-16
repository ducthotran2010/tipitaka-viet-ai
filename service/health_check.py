import logging
from datetime import datetime
from sqlalchemy import text, Engine
from pymongo import MongoClient
from typing import Optional

logger = logging.getLogger(__name__)


class HealthChecker:
    def __init__(self, pg_engine: Engine, mongodb_client: MongoClient) -> None:
        self.pg_engine = pg_engine
        self.mongodb_client = mongodb_client
        self.last_check_ok: datetime = datetime.fromtimestamp(0)
        self.last_health_failure: datetime = datetime.fromtimestamp(0)

    def check_with_cache(self) -> None:
        now = datetime.utcnow()
        # If the last successful check is older than 20 minutes (1200 seconds)
        if (now - self.last_check_ok).total_seconds() > 1200:
            # If a failure was recorded within the last 20 seconds, immediately raise an error
            if (now - self.last_health_failure).total_seconds() <= 20:
                raise RuntimeError(
                    "Health check failed recently. Please try again later.")
            try:
                self.check()
                self.last_check_ok = now
                self.last_health_failure = datetime.fromtimestamp(
                    0)
            except Exception as e:
                self.last_health_failure = now
                raise RuntimeError(f"Health check failed: {e}")

    def check(self) -> None:
        try:
            self.mongodb_client.server_info()
        except Exception as e:
            raise RuntimeError(f"MongoDB health check failed: {e}")

        try:
            with self.pg_engine.connect() as connection:
                result = connection.execute(text("SELECT 1")).scalar()
                if result != 1:
                    raise RuntimeError(
                        "PostgreSQL health check returned unexpected result")
        except Exception as e:
            raise RuntimeError(f"PostgreSQL health check failed: {e}")
