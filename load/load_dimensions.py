import glob
import os

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from infra.alerts import send_status_coverage_alert
from infra.db_connector import get_db_engine
from infra.logger import get_logger
from load.load_facts import add_audit_columns, upsert_to_postgres
from load.scd2 import upsert_scd2_dimension

logger = get_logger(__name__)

DROP_THRESHOLD = 0.3  # abort an entity's load if its row count falls more than 30% vs what's currently loaded

PROCESSED_DIR = os.path.join("data", "processed")

SIMPLE_DIMENSIONS = {
    "cooperatives": ("dim_cooperatives", "codigo_cooperativa"),
    "regionals": ("dim_regionals", "codigo_regional"),
    "volunteers": ("dim_volunteers", "codigo_voluntario"),
    "statuses": ("dim_status", "codigo_situacao"),
    "invoice_statuses": ("dim_status_invoice", "codigo_situacao_boleto"),
}

# Reference dimensions whose code set defines what the extractors can even see.
# Maps the entity to its description column, used to make the alert readable.
STATUS_DIMENSIONS = {
    "statuses": "descricao_situacao",
    "invoice_statuses": "descricao_situacao_boleto",
}

SCD2_DIMENSIONS = {
    "customers": {
        "table": "dim_customers",
        "natural_key": "codigo_associado",
        "monitored_columns": [
            "codigo_situacao", "codigo_voluntario", "codigo_classificacao",
            "codigo_regional", "codigo_cooperativa",
        ],
        "surrogate_key": "sk_customer",
    },
    "vehicles": {
        "table": "dim_vehicles",
        "natural_key": "codigo_veiculo",
        "monitored_columns": [
            "codigo_situacao", "valor_fixo", "codigo_voluntario", "data_contrato",
            "codigo_classificacao", "codigo_regional", "codigo_cooperativa", "valor_fipe_protegido",
        ],
        "surrogate_key": "sk_vehicle",
    },
}


def get_latest_processed_file(entity_name, base_dir=PROCESSED_DIR):
    search_pattern = os.path.join(base_dir, f"{entity_name}_*.parquet")
    files = glob.glob(search_pattern)

    if not files:
        raise FileNotFoundError(f"No processed Parquet file found for entity: {entity_name}")

    return max(files)


def get_current_row_count(engine, table_name, vigente_only=False):
    if not inspect(engine).has_table(table_name):
        return 0
    where_clause = "WHERE vigente" if vigente_only else ""
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table_name} {where_clause}")).scalar()


def assert_no_abnormal_drop(current_count, previous_count, entity_name):
    """Refuses to load if row count collapsed vs. what's already in the table.

    Guards against partial extractions (e.g. an API timeout mid-pagination)
    being mistaken for a legitimate drop in the dataset.
    """
    if previous_count == 0:
        return
    drop_ratio = 1 - (current_count / previous_count)
    if drop_ratio > DROP_THRESHOLD:
        raise ValueError(
            f"Row count for '{entity_name}' dropped {drop_ratio:.0%} "
            f"({previous_count} -> {current_count}). Likely a partial extraction; refusing to load."
        )


def warn_on_status_coverage_change(
    engine: Engine,
    table_name: str,
    key_column: str,
    description_column: str,
    df: pd.DataFrame,
) -> None:
    """Compares the incoming status codes against the ones already in the DW and alerts on any difference.

    The source filters these lists by the API user's permissions, so a status the
    user cannot see is simply absent from the response instead of raising — which
    already caused vehicles in an unseen status to never reach dim_vehicles.
    Never raises: a coverage change is worth a loud warning, not a failed load.
    """
    try:
        if not inspect(engine).has_table(table_name):
            logger.info(f"Table '{table_name}' not found; skipping coverage check on first load.")
            return

        with engine.connect() as conn:
            rows = conn.execute(text(f'SELECT "{key_column}", "{description_column}" FROM {table_name}')).all()

        known = {str(code): desc for code, desc in rows}
        incoming = {
            str(c): d
            for c, d in zip(df[key_column], df[description_column], strict=True)
        }

        added = {c: d for c, d in incoming.items() if c not in known}
        removed = {c: d for c, d in known.items() if c not in incoming}

        if not added and not removed:
            return

        if added:
            logger.warning(f"[{table_name}] New status codes from source: {added}")
        if removed:
            logger.warning(f"[{table_name}] Status codes missing from source: {removed}")

        send_status_coverage_alert(table_name, added, removed)

    except Exception as e:
        logger.error(f"Could not run status coverage check on '{table_name}': {e}")


def run_dimensions_load():
    logger.info("Starting Dimensions Load pipeline...")

    engine = get_db_engine()
    reference_date = pd.Timestamp.now().date()
    success_count = 0
    failed_entities = []

    for entity, (table, natural_key) in SIMPLE_DIMENSIONS.items():
        logger.info(f"Processing load for: {entity.upper()}")
        try:
            file_path = get_latest_processed_file(entity)
            logger.info(f"Reading processed data from: {file_path}")
            df = pd.read_parquet(file_path)

            previous_count = get_current_row_count(engine, table)
            assert_no_abnormal_drop(len(df), previous_count, entity)

            if entity in STATUS_DIMENSIONS:
                warn_on_status_coverage_change(
                    engine, table, natural_key, STATUS_DIMENSIONS[entity], df
                )

            df = add_audit_columns(df, reference_date=reference_date)
            upsert_to_postgres(df, table, natural_key, immutable_columns=["criado_em"])
            logger.info(f"Table '{table}' upserted with {len(df)} rows.")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to load entity '{entity}': {e}")
            failed_entities.append(entity)

    for entity, cfg in SCD2_DIMENSIONS.items():
        logger.info(f"Processing SCD2 load for: {entity.upper()}")
        try:
            file_path = get_latest_processed_file(entity)
            logger.info(f"Reading processed data from: {file_path}")
            df = pd.read_parquet(file_path)

            previous_count = get_current_row_count(engine, cfg["table"], vigente_only=True)
            assert_no_abnormal_drop(len(df), previous_count, entity)

            upsert_scd2_dimension(
                df, cfg["table"], cfg["natural_key"], cfg["monitored_columns"], reference_date,
                cfg["surrogate_key"],
            )
            logger.info(f"Table '{cfg['table']}' SCD2-upserted with {len(df)} current rows.")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to load entity '{entity}': {e}")
            failed_entities.append(entity)

    total_tables = len(SIMPLE_DIMENSIONS) + len(SCD2_DIMENSIONS)
    logger.info(f"Load finished. Successfully loaded {success_count}/{total_tables} tables.")

    if failed_entities:
        raise RuntimeError(
            f"Dimension load finished with failures: {failed_entities}. "
            f"Loaded {success_count}/{total_tables} tables. Facts must not be loaded against "
            f"stale dimensions, and the flow must not report success."
        )


if __name__ == "__main__":
    run_dimensions_load()
