"""Independent staleness check for the data warehouse.

Every other guard here is triggered by a flow that ran: on_failure fires when a
flow fails, and the extraction and load guards run inside one. None of them cover
the flow never starting. That is not hypothetical — the Prefect server's scheduler
crashed and the pipeline silently stopped running for three days,
which was not noticed by accident.

This check therefore must not run under Prefect: an orchestrator cannot be the
watchdog for its own death. It is scheduled by the Windows Task Scheduler, reads
the warehouse and nothing else, and exits non-zero when data is stale.
"""

import sys
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from infra.alerts import send_staleness_alert
from infra.db_connector import get_db_engine
from infra.logger import get_logger

logger = get_logger(__name__)

# The daily run starts at 03:00, so 26h clears one missed night without alerting
# on a run that merely started late.
MAX_AGE_HOURS = 26

# Table -> column stamped when the pipeline last wrote the row. The delinquency
# snapshot is insert-only and has no atualizado_em.
MONITORED_TABLES = {
    "dim_customers": "atualizado_em",
    "dim_vehicles": "atualizado_em",
    "fact_invoices": "atualizado_em",
    "bridge_invoices_vehicles": "atualizado_em",
    "fact_delinquency_snapshot": "criado_em",
}


def collect_ages(engine: Engine) -> dict[str, float | None]:
    """Returns hours colapsed since each monitored table was last written,  None if never."""
    now = datetime.now()
    ages: dict[str, float | None] = {}

    with engine.connect() as conn:
        for table, column in MONITORED_TABLES.items():
            last_written = conn.execute(text(f'SELECT MAX("{column}") FROM {table}')).scalar()
            ages[table] = None if last_written is None else (now - last_written).total_seconds() / 3600

    return ages


def find_stale(ages: dict[str, float | None], max_age_hours: float = MAX_AGE_HOURS) -> dict[str, float | None]:
    """Selects the tables past the age limit. A table never written counts as stale."""
    return {table: age for table, age in ages.items() if age is None or age > max_age_hours}


def main() -> int:
    ages = collect_ages(get_db_engine())

    for table, age in sorted(ages.items()):
        described = "never written" if age is None else f"{age:.1f}h since last write"
        logger.info(f"{table}: {described}")

    stale = find_stale(ages)
    if not stale:
        logger.info(f"All {len(ages)} monitored tables were written within {MAX_AGE_HOURS}h.")
        return 0

    logger.error(f"Warehouse is stale: {sorted(stale)}")
    send_staleness_alert(stale, MAX_AGE_HOURS)
    return 1


if __name__ == "__main__":
    sys.exit(main())