from functools import lru_cache

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine

from infra.config import config
from infra.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_db_engine() -> Engine:
    """Returns a single shared engine/connection pool for the whole process,
    instead of each loader opening its own pool against the same database.

    Built via URL.create rather than an f-string URL: it escapes every component
    (not just the password) and renders the password as *** in repr/str, so a
    connection error that carries the URL cannot print the credential. The
    previous try/except only logged and re-raised — its single net effect was
    exposing that URL — so failures now propagate untouched.
    """
    url = URL.create(
        "postgresql",
        username=config.DB_USER,
        password=config.DB_PASSWORD,
        host=config.DB_HOST,
        port=int(config.DB_PORT),
        database=config.DB_NAME,
    )

    return create_engine(url, pool_pre_ping=True)


if __name__ == "__main__":
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            logger.info("Database connection established successfully.")
    except Exception:
        logger.error("Critical failure during database connection test.")
        raise