from datetime import UTC, datetime

from sqlalchemy import column, insert, table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import DateTime, Text

from infra.db_connector import get_db_engine
from infra.logger import get_logger

logger = get_logger(__name__)

RAW_SCHEMA = "raw"

# Tables are created by sql/ddl/010_raw_schema.sql. The allowlist keeps the
# target an identifier this module chose, never an arbitrary string from a
# caller: table names cannot be bound parameters.
KNOWN_ENTITIES = frozenset(
    {
        "regionals",
        "cooperatives",
        "statuses",
        "volunteers",
        "customers",
        "vehicles",
        "invoices",
        "invoice_statuses",
        "delinquency",
        "invoice_lookups",
    }
)

# Rows per INSERT statement. SQLAlchemy's insertmanyvalues renders a batch of
# rows into one multi-VALUES statement, instead of the one round trip per row
# that executemany over a text() statement costs with psycopg2.
INSERT_BATCH_SIZE = 1000


def _raw_table(entity: str):
    return table(
        entity,
        column("_extracted_at", DateTime(timezone=True)),
        column("_endpoint", Text),
        column("payload", JSONB),
        schema=RAW_SCHEMA,
    )


def write_raw(entity: str, endpoint: str, records: list[dict]) -> datetime:
    """Appends one extraction batch to raw.<entity> and returns its batch timestamp.

    The timestamp is generated once for the whole batch rather than per row, so
    staging models can isolate a single extraction with `_extracted_at = max(...)`.
    The insert runs inside one transaction: a batch lands whole or not at all,
    which keeps the max() filter from ever selecting a truncated extraction.
    """
    if entity not in KNOWN_ENTITIES:
        raise ValueError(f"Unknown raw entity '{entity}'. Known: {sorted(KNOWN_ENTITIES)}")

    if not records:
        raise ValueError(
            f"Refusing to write an empty batch to raw.{entity}. For every entity in this "
            f"pipeline zero records means the extraction failed, not that the source is empty."
        )

    extracted_at = datetime.now(UTC)
    rows = [{"_extracted_at": extracted_at, "_endpoint": endpoint, "payload": record} for record in records]
    statement = insert(_raw_table(entity))

    engine = get_db_engine()
    with engine.begin() as conn:
        for start in range(0, len(rows), INSERT_BATCH_SIZE):
            conn.execute(statement, rows[start : start + INSERT_BATCH_SIZE])

    logger.info(f"raw.{entity}: {len(rows)} records landed at {extracted_at.isoformat()}.")
    return extracted_at
