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


def run_pipeline():
    print(f"🚀 [{datetime.now()}] Starting full pipeline...\n")

    # 1. Extract
    print("═" * 50)
    print("📥 EXTRACT")
    print("═" * 50)
    run_volunteer_extraction()
    run_cooperative_extraction()
    run_regional_extraction()
    run_customer_extraction()
    run_vehicle_extraction()

    # 2. Transform
    print("\n" + "═" * 50)
    print("⚙️  TRANSFORM")
    print("═" * 50)
    transform_volunteers()
    transform_cooperatives()
    transform_regionals()
    transform_customers()
    transform_vehicles()

    # 3. Load
    print("\n" + "═" * 50)
    print("📤 LOAD")
    print("═" * 50)
    run_dimensions_load()

    print(f"\n✅ [{datetime.now()}] Pipeline finished successfully.")


if __name__ == "__main__":
    run_pipeline()