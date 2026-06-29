import os
import glob
import pandas as pd
from sqlalchemy import text, inspect
from sqlalchemy.engine import Connection, Engine
from infra.db_connector import get_db_engine
from infra.logger import get_logger

logger = get_logger(__name__)

FACT_TABLE = "fact_invoices"
PK_COLUMN = "codigo_boleto"


def get_latest_processed_file(entity_name: str) -> str:
    search_pattern = os.path.join("data", "processed", f"{entity_name}_*.parquet")
    files = glob.glob(search_pattern)
    if not files:
        raise FileNotFoundError(f"No processed parquet file found for entity: {entity_name}")
    return max(files)


def _infer_pg_type(dtype) -> str:
    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(dtype):
        return "BIGINT"
    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE PRECISION"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "TIMESTAMP"
    return "TEXT"


def sync_table_schema(conn: Connection, engine: Engine, table_name: str, df: pd.DataFrame) -> None:
    """Adds columns present in df but missing from table_name, preventing schema drift
    when new business-rule columns are introduced upstream after the table already exists."""
    existing_cols = {c["name"] for c in inspect(engine).get_columns(table_name)}
    missing_cols = [c for c in df.columns if c not in existing_cols]
    if not missing_cols:
        return

    logger.warning(f"Schema drift detected on '{table_name}': adding missing columns {missing_cols}")
    for col in missing_cols:
        pg_type = _infer_pg_type(df[col].dtype)
        conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{col}" {pg_type}'))


def upsert_to_postgres(df: pd.DataFrame, table_name: str, pk_column: str):
    engine = get_db_engine()

    if not inspect(engine).has_table(table_name):
        logger.info(f"Table '{table_name}' not found. Creating with primary key on '{pk_column}'...")
        with engine.begin() as conn:
            df.to_sql(table_name, conn, if_exists="replace", index=False, chunksize=1000)
            conn.execute(text(f'ALTER TABLE {table_name} ADD PRIMARY KEY ("{pk_column}")'))
        logger.info(f"Table '{table_name}' created.")
        return

    temp_table = f"_temp_{table_name}"
    cols = ", ".join(f'"{c}"' for c in df.columns)
    updates = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in df.columns if c != pk_column)

    with engine.begin() as conn:
        sync_table_schema(conn, engine, table_name, df)
        df.to_sql(temp_table, conn, if_exists="replace", index=False, chunksize=1000)

        conn.execute(text(f"""
            INSERT INTO {table_name} ({cols})
            SELECT {cols} FROM "{temp_table}"
            ON CONFLICT ("{pk_column}") DO UPDATE SET {updates}
        """))

        conn.execute(text(f'DROP TABLE IF EXISTS "{temp_table}"'))


def run_facts_load():
    logger.info("Starting Facts Load pipeline...")

    try:
        file_path = get_latest_processed_file("invoices")
        logger.info(f"Reading processed data from: {file_path}")
        df = pd.read_parquet(file_path)

        logger.info(f"Upserting {len(df)} rows into '{FACT_TABLE}'...")
        upsert_to_postgres(df, FACT_TABLE, PK_COLUMN)
        logger.info(f"Table '{FACT_TABLE}' successfully updated.")

    except Exception as e:
        logger.error(f"Critical failure in facts load: {e}")
        raise


if __name__ == "__main__":
    run_facts_load()
