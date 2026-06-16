# orchestrators/run_pipeline.py
from extract.extract_volunteers import run_volunteer_extraction
from extract.extract_cooperatives import run_cooperative_extraction
from extract.extract_regionals import run_regional_extraction
from extract.extract_customers import run_customer_extraction
from extract.extract_vehicles import run_vehicle_extraction
from extract.extract_invoices import run_invoice_extraction
from extract.extract_delinquency import run_delinquency_extraction

from transform.transform_volunteers import transform as transform_volunteers
from transform.transform_cooperatives import transform as transform_cooperatives
from transform.transform_regionals import transform as transform_regionals
from transform.transform_customers import transform as transform_customers
from transform.transform_vehicles import transform as transform_vehicles
from transform.transform_invoices import transform as transform_invoices
from transform.transform_delinquency import transform as transform_delinquency

from load.load_dimensions import run_dimensions_load
from load.load_facts import run_facts_load
from load.load_delinquency_snapshot import run_delinquency_snapshot_load

from infra.logger import get_logger

logger = get_logger(__name__)


def run_pipeline():
    logger.info("Starting full pipeline...")

    run_volunteer_extraction()
    run_cooperative_extraction()
    run_regional_extraction()
    run_customer_extraction()
    run_vehicle_extraction()
    run_invoice_extraction()
    run_delinquency_extraction()

    transform_volunteers()
    transform_cooperatives()
    transform_regionals()
    transform_customers()
    transform_vehicles()
    transform_invoices()
    transform_delinquency()

    run_dimensions_load()
    run_facts_load()
    run_delinquency_snapshot_load()

    logger.info("Pipeline finished successfully.")


if __name__ == "__main__":
    run_pipeline()