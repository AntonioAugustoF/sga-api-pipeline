import pandas as pd
from sqlalchemy import text
from infra.db_connector import get_db_engine
from infra.logger import get_logger
from load.load_facts import upsert_to_postgres, add_audit_columns
from load.load_invoice_vehicle_bridge import BRIDGE_TABLE, PK_COLUMNS
from transform.business_rules import allocate_invoice_value_by_vehicle

logger = get_logger(__name__)


def run_backfill():
    """One-off backfill of bridge_invoices_vehicles from the invoices already in
    fact_invoices. load_invoices_initial.py (the 2019+ historical loader) predates
    the bridge and never populated it, so only the daily pipeline's latest batch
    had bridge rows. fact_invoices already carries the raw 'veiculo' column for
    its full history, so this rebuilds the bridge without hitting the API again."""
    engine = get_db_engine()

    logger.info("Reading codigo_boleto/veiculo/valor_boleto from fact_invoices...")
    with engine.connect() as conn:
        df = pd.read_sql(
            text("""
                SELECT codigo_boleto, veiculo, valor_boleto
                FROM fact_invoices
                WHERE veiculo IS NOT NULL AND veiculo != ''
            """),
            conn,
        )
    logger.info(f"{len(df)} invoices read from fact_invoices.")

    df["veiculo"] = df["veiculo"].str.split(",")
    bridge_df = allocate_invoice_value_by_vehicle(df, "codigo_boleto", "veiculo", "valor_boleto")
    bridge_df = add_audit_columns(bridge_df, reference_date=pd.Timestamp.now().date())

    logger.info(f"Backfilling {len(bridge_df)} rows into '{BRIDGE_TABLE}'...")
    upsert_to_postgres(bridge_df, BRIDGE_TABLE, PK_COLUMNS, immutable_columns=["criado_em"])
    logger.info("Backfill complete.")


if __name__ == "__main__":
    run_backfill()
