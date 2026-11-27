from collections.abc import Callable

from prefect import flow, task

from extract.extract_cooperatives import run_cooperative_extraction
from extract.extract_customers import run_customer_extraction
from extract.extract_delinquency import run_delinquency_extraction
from extract.extract_invoice_lookups import run_invoice_lookup_extraction
from extract.extract_invoices import run_invoice_extraction
from extract.extract_regionals import run_regional_extraction
from extract.extract_statuses import run_status_extraction
from extract.extract_vehicles import run_vehicle_extraction
from extract.extract_volunteers import run_volunteer_extraction
from infra.alerts import send_failure_alert
from infra.config import config
from infra.dbt_runner import run_dbt_build
from infra.logger import get_logger

logger = get_logger(__name__)

# Independent of each other: one failing does not stop the rest from landing.
INDEPENDENT_EXTRACTIONS: dict[str, Callable[[], None]] = {
    "statuses": run_status_extraction,
    "volunteers": run_volunteer_extraction,
    "cooperatives": run_cooperative_extraction,
    "regionals": run_regional_extraction,
    "customers": run_customer_extraction,
    "vehicles": run_vehicle_extraction,
    "invoices": run_invoice_extraction,
    "delinquency": run_delinquency_extraction,
}

# Task-level retry on top of the per-request retry in infra/retry.py: that one
# absorbs a dropped connection, this one a longer outage of the source. A retry
# re-runs the whole extraction, which is safe because raw is append-only and a
# batch lands whole or not at all.
EXTRACTION_RETRIES = 1
EXTRACTION_RETRY_DELAY_SECONDS = 600


class ExtractionFailedError(RuntimeError):
    """Raised before dbt when any extraction failed, so no model builds on a stale batch."""


def _as_task(name: str, fn: Callable[[], None]):
    return task(
        fn,
        name=f"extract-{name}",
        retries=EXTRACTION_RETRIES,
        retry_delay_seconds=EXTRACTION_RETRY_DELAY_SECONDS,
    )


def _raise_if_failed(states: dict[str, object]) -> None:
    failed = [name for name, state in states.items() if state.is_failed() or state.is_crashed()]
    if failed:
        raise ExtractionFailedError(
            f"{len(failed)} extraction(s) failed: {', '.join(failed)}. dbt was not run, so the warehouse "
            "still reflects the previous night; see each task's log for the cause."
        )


@flow(
    name="sga-pipeline-diario",
    timeout_seconds=21600,             # 6h: corta uma execução travada; acima de dias lentos legítimos
    on_failure=[send_failure_alert],   # cobre Failed e TimedOut (ambos são tipo FAILED)
    on_crashed=[send_failure_alert],   # cobre Crashed (processo morto, infra, etc.)
)
def run_pipeline() -> None:
    """Extracts every entity into raw, then lets dbt build the warehouse from it.

    Each extraction is a Prefect task with its own retry and its own state, so a
    failed entity is visible by name and a transient failure late in the run no
    longer throws away the ones that already landed. The flow still fails loudly:
    if anything failed, dbt does not run — a fact must not be merged against a
    dimension built from yesterday's batch.

    The invoice reconciliation runs last among the extractions because its
    candidate set is computed against the delinquency batch of this same run.
    Its failure does not hold back dbt; it fails the flow once dbt is done.
    """
    logger.info("Starting full pipeline...")

    config.validate()

    states = {
        name: _as_task(name, fn)(return_state=True) for name, fn in INDEPENDENT_EXTRACTIONS.items()
    }
    _raise_if_failed(states)

    # The reconciliation only corrects rows the listing already brought; if it
    # fails, tonight's batches are still complete and the warehouse is still
    # built from them. The flow fails afterwards, so the alert fires anyway.
    # Not retried: a 403 from the source means "stop calling".
    lookup_state = task(run_invoice_lookup_extraction, name="extract-invoice-lookups")(return_state=True)

    run_dbt_build()

    _raise_if_failed({"invoice-lookups": lookup_state})

    logger.info("Pipeline finished successfully.")


if __name__ == "__main__":
    run_pipeline()
