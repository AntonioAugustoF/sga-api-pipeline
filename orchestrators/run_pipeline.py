# orchestrators/run_pipeline.py
from datetime import datetime

from extract.extract_volunteers import run_volunteer_extraction
from extract.extract_cooperatives import run_cooperative_extraction
from extract.extract_regionals import run_regional_extraction
from extract.extract_customers import run_customer_extraction
from extract.extract_vehicles import run_vehicle_extraction

from transform.transform_volunteers import transform as transform_volunteers
from transform.transform_cooperatives import transform as transform_cooperatives
from transform.transform_regionals import transform as transform_regionals
from transform.transform_customers import transform as transform_customers
from transform.transform_vehicles import transform as transform_vehicles

from load.load_dimensions import run_dimensions_load
from load.load_facts import run_facts_load

from infra.logger import get_logger

logger = get_logger(__name__)


def run_pipeline():
    logger.info("Starting full pipeline...")

    run_volunteer_extraction()
    run_cooperative_extraction()
    run_regional_extraction()
    run_customer_extraction()
    run_vehicle_extraction()

    transform_volunteers()
    transform_cooperatives()
    transform_regionals()
    transform_customers()
    transform_vehicles()

    run_dimensions_load()
    run_facts_load()

    logger.info("Pipeline finished successfully.")


if __name__ == "__main__":
    run_pipeline()