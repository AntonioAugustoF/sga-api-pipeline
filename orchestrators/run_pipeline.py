from prefect import flow

from extract.extract_cooperatives import run_cooperative_extraction
from extract.extract_customers import run_customer_extraction
from extract.extract_delinquency import run_delinquency_extraction
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

@flow(
    name="sga-pipeline-diario",
    timeout_seconds=21600,             # 6h: corta uma execução travada; acima de dias lentos legítimos
    on_failure=[send_failure_alert],   # cobre Failed e TimedOut (ambos são tipo FAILED)
    on_crashed=[send_failure_alert],   # cobre Crashed (processo morto, infra, etc.)
)
def run_pipeline():
    """Extracts every entity into raw, then lets dbt build the warehouse from it.

    This is the whole pipeline now. The transform and load steps that used to
    sit between these two blocks were deleted at the cutover: the business
    rules they held are expressed in SQL under dbt/models, and the warehouse
    they wrote is rebuilt from raw on every run.

    Extraction still comes first and still fails loudly. It is the only step
    that talks to something outside this machine, and a batch that does not
    land is missing data for every model downstream of it -- there is no
    second path left to cover for it.
    """
    logger.info("Starting full pipeline...")

    config.validate()

    run_status_extraction()
    run_volunteer_extraction()
    run_cooperative_extraction()
    run_regional_extraction()
    run_customer_extraction()
    run_vehicle_extraction()
    run_invoice_extraction()
    run_delinquency_extraction()

    run_dbt_build()

    logger.info("Pipeline finished successfully.")


if __name__ == "__main__":
    run_pipeline()
