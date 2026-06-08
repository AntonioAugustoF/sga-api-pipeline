from sqlalchemy import create_engine
from infra.config import config
from infra.logger import get_logger
from urllib.parse import quote_plus

logger = get_logger(__name__)


def get_db_engine():
    try:
        connection_url = (
            f"postgresql://{config.DB_USER}:{quote_plus(config.DB_PASSWORD)}"
            f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
        )

        engine = create_engine(connection_url)
        return engine

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