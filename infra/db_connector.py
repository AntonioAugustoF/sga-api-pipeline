from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from infra.config import config
from infra.logger import get_logger
from urllib.parse import quote_plus

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_db_engine() -> Engine:
    """Returns a single shared engine/connection pool for the whole process,
    instead of each loader opening its own pool against the same database."""
    try:
        connection_url = (
            f"postgresql://{config.DB_USER}:{quote_plus(config.DB_PASSWORD)}"
            f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
        )

        return create_engine(connection_url, pool_pre_ping=True)

    except Exception as e:
        logger.error(f"Failed to configure database engine: {e}")
        raise


if __name__ == "__main__":
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            logger.info("Database connection established successfully.")
    except Exception as e:
        logger.error("Critical failure during database connection test.")
        raise