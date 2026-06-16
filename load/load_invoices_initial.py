import pandas as pd
from datetime import datetime, timedelta
from infra.authenticator import authenticate_user
from infra.logger import get_logger
from infra.transformations import (
    rename_columns,
    remove_duplicates,
    remove_empty_rows,
    cast_string_columns,
    cast_date_columns,
    cast_numeric_columns,
)
from extract.extract_invoices import get_invoice_statuses, _fetch_by_status
from load.load_facts import upsert_to_postgres, FACT_TABLE, PK_COLUMN
from transform.transform_invoices import STR_COLS, DATE_COLS, NUMERIC_COLS

logger = get_logger(__name__)

START_DATE = datetime(2019, 1, 1)
FMT = "%d/%m/%Y"


def _fmt(dt: datetime) -> str:
    return dt.strftime(FMT)


def _month_ranges(start: datetime, end: datetime):
    current = start.replace(day=1)
    while current <= end:
        if current.month == 12:
            next_month = current.replace(year=current.year + 1, month=1, day=1)
        else:
            next_month = current.replace(month=current.month + 1, day=1)
        yield current, next_month - timedelta(days=1)
        current = next_month


def run_initial_load():
    logger.info(f"Starting initial invoices load from {_fmt(START_DATE)}...")

    user_token = authenticate_user()
    status_list = get_invoice_statuses(user_token)
    logger.info(f"Statuses found: {status_list}")

    today = datetime.now()
    merged = {}

    for month_start, month_end in _month_ranges(START_DATE, today):
        label = month_start.strftime("%Y-%m")
        filters = {
            "data_emissao_inicial": _fmt(month_start),
            "data_emissao_final": _fmt(month_end),
        }
        logger.info(f"[{label}] Extracting...")

        for status in status_list:
            try:
                records = _fetch_by_status(status, user_token, filters)
                for record in records:
                    merged[record.get("codigo_boleto")] = record
            except Exception as e:
                logger.warning(f"[{label}] Status {status}: {e}")

    logger.info(f"Total unique invoices extracted: {len(merged)}")

    df = pd.DataFrame(list(merged.values()))
    df = rename_columns(df)
    df = cast_string_columns(df, STR_COLS)
    df = cast_date_columns(df, DATE_COLS)
    df = cast_numeric_columns(df, NUMERIC_COLS)
    df = remove_duplicates(df, subset=["codigo_boleto"])
    df = remove_empty_rows(df)

    logger.info(f"Upserting {len(df)} rows into '{FACT_TABLE}'...")
    upsert_to_postgres(df, FACT_TABLE, PK_COLUMN)
    logger.info("Initial load complete.")


if __name__ == "__main__":
    run_initial_load()
