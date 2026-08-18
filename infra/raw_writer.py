import json
from datetime import datetime, timezone

from sqlalchemy import text

from infra.alerts import send_raw_landing_alert
from infra.db_connector import get_db_engine
from infra.logger import get_logger

logger = get_logger(__name__)

RAW_SCHEMA = "raw"

# Tables are created by sql/ddl/010_raw_schema.sql. The allowlist is what makes
# the f-string below safe: a table name is an identifier, which cannot be passed
# as a bound parameter, so interpolating an unchecked entity string would be an
# injection point.
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
    }
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

    extracted_at = datetime.now(timezone.utc)
    statement = text(
        f"INSERT INTO {RAW_SCHEMA}.{entity} (_extracted_at, _endpoint, payload) "
        "VALUES (:extracted_at, :endpoint, CAST(:payload as jsonb))"
    )
    rows = [
        {
            "extracted_at": extracted_at,
            "endpoint": endpoint,
            "payload": json.dumps(record, ensure_ascii=False),
        }
        for record in records
    ]

    engine = get_db_engine()
    with engine.begin() as conn:
        conn.execute(statement, rows)

    logger.info(f"raw.{entity}: {len(rows)} records landed at {extracted_at.isoformat()}.")
    return extracted_at


def write_raw_shadow(entity: str, endpoint: str, records: list[dict]) -> None:
    """Lands a batch in raw without letting a raw-layer failure break the pipeline.
    
    Temporary, and valid only while raw runs in parallel with the file-based path
    (phases 0 to 4 of the ELT migration). Raising here would let a bug in a layer
    nothing consumes yet take production down.
    
    THis is not silent degradation: the failure raises a Discord alert, which is
    the loud part. Delete this function at cutover, when raw becomes the only
    source and failing to land must stop the flow.
    """
    try:
        write_raw(entity, endpoint, records)
    except Exception as e:
        logger.error(f"Failed to land raw.{entity}: {e}")
        send_raw_landing_alert(entity, str(e))