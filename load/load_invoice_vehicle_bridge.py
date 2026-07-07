import os
import glob
import pandas as pd
from infra.logger import get_logger
from load.load_facts import upsert_to_postgres, add_audit_columns

logger = get_logger(__name__)

BRIDGE_TABLE = "bridge_invoices_vehicles"
PK_COLUMNS = ["codigo_boleto", "codigo_veiculo"]


def get_latest_processed_file(entity_name: str) -> str:
    search_pattern = os.path.join("data", "processed", f"{entity_name}_*.parquet")
    files = glob.glob(search_pattern)
    if not files:
        raise FileNotFoundError(f"No processed parquet file found for entity: {entity_name}")
    return max(files)


def run_bridge_load():
    logger.info("Starting Invoice-Vehicle Bridge Load pipeline...")

    try:
        file_path = get_latest_processed_file("invoice_vehicle_bridge")
        logger.info(f"Reading processed data from: {file_path}")
        df = pd.read_parquet(file_path)
        df = add_audit_columns(df, reference_date=pd.Timestamp.now().date())

        logger.info(f"Upserting {len(df)} rows into '{BRIDGE_TABLE}'...")
        upsert_to_postgres(df, BRIDGE_TABLE, PK_COLUMNS, immutable_columns=["criado_em"])
        logger.info(f"Table '{BRIDGE_TABLE}' successfully updated.")

    except Exception as e:
        logger.error(f"Critical failure in invoice-vehicle bridge load: {e}")
        raise


if __name__ == "__main__":
    run_bridge_load()
