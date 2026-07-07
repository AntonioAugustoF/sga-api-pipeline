import os
import glob
import pandas as pd
from datetime import date
from sqlalchemy import text, inspect
from infra.db_connector import get_db_engine
from infra.logger import get_logger
from load.load_facts import resolve_point_in_time_sk
from load.load_facts import sync_table_schema

logger = get_logger(__name__)

SNAPSHOT_TABLE = "fact_delinquency_snapshot"
PK_COLUMNS = ["codigo_boleto", "dt_referencia"]


def get_latest_processed_file(entity_name: str) -> str:
    search_pattern = os.path.join("data", "processed", f"{entity_name}_*.parquet")
    files = glob.glob(search_pattern)
    if not files:
        raise FileNotFoundError(f"No processed parquet file found for entity: {entity_name}")
    return max(files)


def load_delinquency_snapshot():
    engine = get_db_engine()

    file_path = get_latest_processed_file("delinquency")
    logger.info(f"Reading processed data from: {file_path}")
    df = pd.read_parquet(file_path)
    df = resolve_point_in_time_sk(
    engine, df,
    dim_table="dim_customers",
    dim_natural_key="codigo_associado",
    dim_sk_col="sk_customer",
    fact_natural_key="codigo_associado",
    fact_date_col="data_emissao",
    )
    df["criado_em"] = pd.Timestamp.now()

    today = date.today()
    cols = ", ".join(f'"{c}"' for c in df.columns)
    pk_constraint = ", ".join(f'"{c}"' for c in PK_COLUMNS)

    with engine.begin() as conn:
        if not inspect(engine).has_table(SNAPSHOT_TABLE):
            logger.info(f"Table '{SNAPSHOT_TABLE}' not found. Creating...")
            df.to_sql(SNAPSHOT_TABLE, conn, if_exists="replace", index=False, chunksize=1000)
            conn.execute(text(f'ALTER TABLE {SNAPSHOT_TABLE} ADD PRIMARY KEY ({pk_constraint})'))
            logger.info(f"Table '{SNAPSHOT_TABLE}' created with {len(df)} rows.")
            return

        sync_table_schema(conn, engine, SNAPSHOT_TABLE, df)

        logger.info(f"Deleting existing rows for dt_referencia = {today}...")
        conn.execute(text(f"DELETE FROM {SNAPSHOT_TABLE} WHERE dt_referencia = :dt"), {"dt": today})

        temp_table = f"_temp_{SNAPSHOT_TABLE}"
        df.to_sql(temp_table, conn, if_exists="replace", index=False, chunksize=1000)
        conn.execute(text(f'INSERT INTO {SNAPSHOT_TABLE} ({cols}) SELECT {cols} FROM "{temp_table}"'))
        conn.execute(text(f'DROP TABLE IF EXISTS "{temp_table}"'))

    logger.info(f"Snapshot for {today} loaded: {len(df)} rows into '{SNAPSHOT_TABLE}'.")


def run_delinquency_snapshot_load():
    logger.info("Starting Delinquency Snapshot Load...")
    try:
        load_delinquency_snapshot()
    except Exception as e:
        logger.error(f"Critical failure in delinquency snapshot load: {e}")
        raise


if __name__ == "__main__":
    run_delinquency_snapshot_load()
