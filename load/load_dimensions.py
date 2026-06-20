import os
import glob
import pandas as pd
from infra.db_connector import get_db_engine
from infra.logger import get_logger

logger = get_logger(__name__)


def get_latest_processed_file(entity_name, base_dir=os.path.join("data", "processed")):
    search_pattern = os.path.join(base_dir, f"{entity_name}_*.parquet")
    files = glob.glob(search_pattern)

    if not files:
        raise FileNotFoundError(f"No processed Parquet file found for entity: {entity_name}")

    return max(files)


def load_entity_to_postgres(entity_name, table_name):
    try:
        file_path = get_latest_processed_file(entity_name)
        logger.info(f"Reading processed data from: {file_path}")
        df = pd.read_parquet(file_path)

        engine = get_db_engine()

        logger.info(f"Loading {len(df)} rows into table '{table_name}'...")
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="replace",
            index=False,
            chunksize=1000
        )
        logger.info(f"Table '{table_name}' successfully updated.")

    except Exception as e:
        logger.error(f"Failed to load entity '{entity_name}': {e}")
        raise e


def load_history_to_postgres(df_history, table_name):
    try:
        engine = get_db_engine()

        logger.info(f"Appending {len(df_history)} rows into history table '{table_name}'...")
        df_history.to_sql(
            name=table_name,
            con=engine,
            if_exists="append",
            index=False,
            chunksize=1000
        )
        logger.info(f"History table '{table_name}' updated.")

    except Exception as e:
        logger.error(f"Failed to load history '{table_name}': {e}")
        raise e


def run_dimensions_load():
    logger.info("Starting Dimensions Load pipeline...")

    dimensions_to_load = {
        "vehicles": "dim_vehicles",
        "customers": "dim_customers",
        "volunteers": "dim_volunteers",
        "cooperatives": "dim_cooperatives",
        "regionals": "dim_regionals"
    }

    history_dir = os.path.join("data", "processed", "history")
    history_tables = {
        "vehicles": "dim_vehicles_history",
        "customers": "dim_customers_history",
    }

    success_count = 0
    failed_entities = []

    for entity, table in dimensions_to_load.items():
        logger.info(f"Processing load for: {entity.upper()}")
        try:
            load_entity_to_postgres(entity, table)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to load entity '{entity}': {e}")
            failed_entities.append(entity)

    logger.info("Processing history tables...")

    for entity, table in history_tables.items():
        try:
            history_path = get_latest_processed_file(entity, base_dir=history_dir)
            logger.info(f"Reading history data from: {history_path}")
            df_history = pd.read_parquet(history_path)
            load_history_to_postgres(df_history, table)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to load {entity} history: {e}")
            failed_entities.append(f"{entity}_history")

    total_tables = len(dimensions_to_load) + len(history_tables)
    logger.info(f"Load finished. Successfully loaded {success_count}/{total_tables} tables.")
    if failed_entities:
        logger.warning(f"Failed entities: {failed_entities}")


if __name__ == "__main__":
    run_dimensions_load()