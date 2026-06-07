import os
import glob
from datetime import datetime
import pandas as pd
from infra.db_connector import get_db_engine
from transform.transform_vehicles import transform as transform_vehicles
from transform.transform_customers import transform as transform_customers


def get_latest_processed_file(entity_name):
    """Finds the most recent Parquet file for a given entity in the processed layer."""
    search_pattern = os.path.join("data", "processed", f"{entity_name}_*.parquet")
    files = glob.glob(search_pattern)

    if not files:
        raise FileNotFoundError(f"⚠️ No processed Parquet file found for entity: {entity_name}")

    return max(files)


def load_entity_to_postgres(entity_name, table_name):
    """Reads the latest Parquet file and loads it into the PostgreSQL database."""
    try:
        file_path = get_latest_processed_file(entity_name)
        print(f"📖 Reading processed data from: {file_path}")
        df = pd.read_parquet(file_path)

        engine = get_db_engine()

        print(f"🚀 Loading {len(df)} rows into database table '{table_name}'...")
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="replace",
            index=False,
            chunksize=1000
        )
        print(f"✅ Table '{table_name}' successfully updated.")

    except Exception as e:
        print(f"🚨 Failed to load entity '{entity_name}': {e}")
        raise e


def load_history_to_postgres(df_history, table_name):
    """Appends the history DataFrame into the PostgreSQL history table."""
    try:
        engine = get_db_engine()

        print(f"🚀 Appending {len(df_history)} rows into history table '{table_name}'...")
        df_history.to_sql(
            name=table_name,
            con=engine,
            if_exists="append",
            index=False,
            chunksize=1000
        )
        print(f"✅ History table '{table_name}' updated.")

    except Exception as e:
        print(f"🚨 Failed to load history '{table_name}': {e}")
        raise e


def run_dimensions_load():
    """Orchestrates the loading process for all dimension tables."""
    print(f"⏳ [{datetime.now()}] Starting Dimensions Load pipeline...")

    dimensions_to_load = {
        "vehicles": "dim_vehicles",
        "customers": "dim_customers",
        "volunteers": "dim_volunteers",
        "cooperatives": "dim_cooperatives",
        "regionals": "dim_regionals"
    }

    success_count = 0

    for entity, table in dimensions_to_load.items():
        print(f"\n──────────────────────────────────────────────────")
        print(f"📦 Processing load for: {entity.upper()}")
        try:
            load_entity_to_postgres(entity, table)
            success_count += 1
        except Exception:
            continue

    # Load history tables
    print(f"\n──────────────────────────────────────────────────")
    print(f"📦 Processing history tables...")

    try:
        _, df_vehicles_history = transform_vehicles()
        load_history_to_postgres(df_vehicles_history, "dim_vehicles_history")
        success_count += 1
    except Exception as e:
        print(f"🚨 Failed to load vehicles history: {e}")

    try:
        _, df_customers_history = transform_customers()
        load_history_to_postgres(df_customers_history, "dim_customers_history")
        success_count += 1
    except Exception as e:
        print(f"🚨 Failed to load customers history: {e}")

    print(f"\n📊 Load execution finished. Successfully loaded {success_count}/{len(dimensions_to_load) + 2} tables.")


if __name__ == "__main__":
    run_dimensions_load()