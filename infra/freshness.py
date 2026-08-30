"""Independent staleness check for the data warehouse.

Every other guard here is triggered by a flow that ran: on_failure fires when a
flow fails, and the extraction guard runs inside one. None of them cover the
flow never starting. That is not hypothetical — the Prefect server's scheduler
crashed and the pipeline silently stopped running for three days,
which was not noticed by accident.

This check therefore must not run under Prefect: an orchestrator cannot be the
watchdog for its own death. It is scheduled by the Windows Task Scheduler, reads
the warehouse and nothing else, and exits non-zero when data is stale.
"""

import sys

from sqlalchemy import text
from sqlalchemy.engine import Engine

from infra.alerts import send_staleness_alert
from infra.db_connector import get_db_engine
from infra.logger import get_logger

logger = get_logger(__name__)

# The daily run starts at 03:00, so 26h clears one missed night without alerting
# on a run that merely started late.
MAX_AGE_HOURS = 26

# Table -> the column that proves the pipeline reached it.
#
# Choosing these columns after the cutover took some care. The obvious
# candidate, criado_em on the facts, is wrong: it sits in merge_exclude_columns
# so that it records when a row first appeared and survives later merges. Its
# maximum is the age of the newest invoice, not of the last run, and a quiet
# day with no new invoices would be reported as a dead pipeline.
#
# dim_customers and dim_vehicles are materialised as tables and rebuilt in full
# on every dbt run, so every row is restamped and criado_em means what this
# check needs it to mean.
#
# fact_delinquency_snapshot is watched through dt_referencia instead, which is a
# stronger statement than a timestamp: it asserts that the photograph for the
# day exists. Read as hours since that date's midnight it lands on the same
# scale as the others — today's snapshot is at most 24h old, and yesterday's is
# already past the 26h limit by the time the 06:00 check runs.
MONITORED_TABLES = {
    "analytics.dim_customers": "criado_em",
    "analytics.dim_vehicles": "criado_em",
    "analytics.fact_delinquency_snapshot": "dt_referencia",
}


def collect_ages(engine: Engine) -> dict[str, float | None]:
    """Returns hours elapsed since each monitored table was last written, None if never.

    The subtraction happens in SQL rather than in Python. criado_em is
    timestamptz and this script runs from the Windows Task Scheduler, whose
    idea of local time need not match the server's; comparing against now()
    inside the same session removes the question.
    """
    ages: dict[str, float | None] = {}

    with engine.connect() as conn:
        for table, column in MONITORED_TABLES.items():
            statement = text(
                f'SELECT EXTRACT(EPOCH FROM (now() - MAX("{column}")::timestamptz)) / 3600 FROM {table}'
            )
            age = conn.execute(statement).scalar()
            ages[table] = None if age is None else float(age)

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
