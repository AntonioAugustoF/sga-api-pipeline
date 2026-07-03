import os
import glob
from datetime import date, datetime
import pandas as pd
from sqlalchemy import text, inspect, types as sa_types
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


def _infer_pg_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series.dtype):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(series.dtype):
        return "BIGINT"
    if pd.api.types.is_float_dtype(series.dtype):
        return "DOUBLE PRECISION"
    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        return "TIMESTAMP"

    # cast_date_columns yields object-dtype columns of Python date/datetime instances,
    # which the dtype checks above can't see.
    sample = series.dropna()
    if not sample.empty and isinstance(sample.iloc[0], datetime):
        return "TIMESTAMP"
    if not sample.empty and isinstance(sample.iloc[0], date):
        return "DATE"
    return "TEXT"


def _infer_sa_type(series: pd.Series):
    if pd.api.types.is_bool_dtype(series.dtype): return sa_types.Boolean()
    if pd.api.types.is_integer_dtype(series.dtype): return sa_types.BigInteger()
    if pd.api.types.is_float_dtype(series.dtype): return sa_types.Float()
    if pd.api.types.is_datetime64_any_dtype(series.dtype): return sa_types.DateTime()
    sample = series.dropna()
    if not sample.empty and isinstance(sample.iloc[0], datetime): return sa_types.DateTime()
    if not sample.empty and isinstance(sample.iloc[0], date): return sa_types.Date()
    return sa_types.Text()


def sync_table_schema(conn: Connection, engine: Engine, table_name: str, df: pd.DataFrame) -> None:
    """Adds columns present in df but missing from table_name, preventing schema drift
    when new business-rule columns are introduced upstream after the table already exists."""
    existing_cols = {c["name"] for c in inspect(engine).get_columns(table_name)}
    missing_cols = [c for c in df.columns if c not in existing_cols]
    if not missing_cols:
        return

    logger.warning(f"Schema drift detected on '{table_name}': adding missing columns {missing_cols}")
    for col in missing_cols:
        pg_type = _infer_pg_type(df[col])
        conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{col}" {pg_type}'))


def resolve_point_in_time_sk(
        engine: Engine,
        df: pd.DataFrame,
        dim_table: str,
        dim_natural_key: str,
        dim_sk_col: str,
        fact_natural_key: str,
        fact_date_col: str,
    ) -> pd.DataFrame:
        """
        Adds dim_sk_col to df via a point-in-time join against a SCD2 dimension.
        Each fact row receives the SK of the dimension version that was effective
        on fact_date_col. Returns NULL when no match or when the dimension table
        does not yet exist.
        """
        if not inspect(engine).has_table(dim_table):
            logger.warning(
                f"Dimension table '{dim_table}' not found; '{dim_sk_col}' will be NULL."
            )
            df[dim_sk_col] = None
            return df
        
        with engine.connect() as conn:
            dim_df = pd.read_sql(
                f'SELECT "{dim_natural_key}", "{dim_sk_col}", valido_de, valido_ate FROM {dim_table}',
                conn,
            )
        
        dim_df["valido_de"] = pd.to_datetime(dim_df["valido_de"]).dt.date
        dim_df["valido_ate"] = pd.to_datetime(dim_df["valido_ate"]).dt.date

        keys = df[[fact_natural_key, fact_date_col]].copy().reset_index()
        keys[fact_date_col] = pd.to_datetime(keys[fact_date_col]).dt.date

        merged = keys.merge(dim_df, left_on=fact_natural_key, right_on=dim_natural_key, how="left")
        mask = (merged["valido_de"] <= merged[fact_date_col]) & (
            merged["valido_ate"].isna() | (merged["valido_ate"] > merged[fact_date_col])
        )
        resolved = merged[mask].drop_duplicates(subset=["index"])

        df = df.copy()
        df[dim_sk_col] = df.index.map(resolved.set_index("index")[dim_sk_col])
        return df


def upsert_to_postgres(df: pd.DataFrame, table_name: str, pk_column: str):
    engine = get_db_engine()

    dtype_map = {col: _infer_sa_type(df[col]) for col in df.columns}

    if not inspect(engine).has_table(table_name):
        logger.info(f"Table '{table_name}' not found. Creating with primary key on '{pk_column}'...")
        with engine.begin() as conn:
            df.to_sql(table_name, conn, if_exists="replace", index=False, chunksize=1000, dtype=dtype_map)
            conn.execute(text(f'ALTER TABLE {table_name} ADD PRIMARY KEY ("{pk_column}")'))
        logger.info(f"Table '{table_name}' created.")
        return

    temp_table = f"_temp_{table_name}"
    cols = ", ".join(f'"{c}"' for c in df.columns)
    updates = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in df.columns if c != pk_column)

    with engine.begin() as conn:
        sync_table_schema(conn, engine, table_name, df)
        df.to_sql(temp_table, conn, if_exists="replace", index=False, chunksize=1000, dtype=dtype_map)

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

        engine = get_db_engine()
        df = resolve_point_in_time_sk(
            engine, df,
            dim_table="dim_customers",
            dim_natural_key="codigo_associado",
            dim_sk_col="sk_customer",
            fact_natural_key="codigo_associado",
            fact_date_col="data_emissao",
        )

        logger.info(f"Upserting {len(df)} rows into '{FACT_TABLE}'...")
        upsert_to_postgres(df, FACT_TABLE, PK_COLUMN)
        logger.info(f"Table '{FACT_TABLE}' successfully updated.")

    except Exception as e:
        logger.error(f"Critical failure in facts load: {e}")
        raise


if __name__ == "__main__":
    run_facts_load()
