import argparse
from datetime import date, datetime, timedelta

from infra.api_fetcher import APIFetcher
from infra.authenticator import authenticate_user
from infra.config import config
from infra.extraction_guard import assert_extraction_complete
from infra.logger import get_logger
from infra.raw_writer import write_raw

logger = get_logger(__name__)

FMT = "%d/%m/%Y"
INVOICE_ENDPOINT = "/listar/boleto"
INVOICE_PAGE_SIZE = 1000
INVOICE_TIMEOUT_SECONDS = 60


def _fmt(dt: datetime) -> str:
    return dt.strftime(FMT)


def build_invoice_fetcher(user_token: str) -> APIFetcher:
    return APIFetcher(config.API_BASE_URL, user_token, page_size=INVOICE_PAGE_SIZE, timeout=INVOICE_TIMEOUT_SECONDS)


def get_invoice_statuses(fetcher: APIFetcher) -> list[str]:
    return [s["codigo_situacaoboleto"] for s in fetcher.fetch_all("/listar/situacao-boleto/todos")]


def fetch_invoices_by_status(status_code: str | int, fetcher: APIFetcher, date_filters: dict[str, str]) -> list[dict]:
    """Every invoice in one status matching the date filters. A 406 yields []."""
    records = fetcher.fetch_by_page_number(
        endpoint=INVOICE_ENDPOINT,
        base_payload={"codigo_situacao": int(status_code), **date_filters},
        page_param="inicio_paginacao",
        page_size_param="quantidade_por_pagina",
        items_key="boletos",
        total_key="total_boletos",
    )
    for boleto in records:
        boleto["codigo_situacao"] = status_code
    return records


def _extract_for_all_statuses(
    fetcher: APIFetcher, status_list: list[str], date_filters: dict[str, str], label: str
) -> tuple[list[dict], dict[str, str]]:
    all_records: list[dict] = []
    failures: dict[str, str] = {}
    for status in status_list:
        try:
            records = fetch_invoices_by_status(status, fetcher, date_filters)
            logger.info(f"[{label}] Status {status}: {len(records)} invoices extracted total.")
            all_records.extend(records)
        except Exception as e:
            logger.warning(f"[{label}] Error extracting status {status}: {e}")
            failures[f"{label}/{status}"] = str(e)
    return all_records, failures


def extract_new_invoices(fetcher: APIFetcher, status_list: list[str]) -> tuple[list[dict], dict[str, str]]:
    today = datetime.now()
    filters = {
        "data_emissao_inicial": _fmt(today - timedelta(days=7)),
        "data_emissao_final": _fmt(today - timedelta(days=1)),
    }
    logger.info(f"[NEW] Extracting by emissao: {filters['data_emissao_inicial']} to {filters['data_emissao_final']}")
    return _extract_for_all_statuses(fetcher, status_list, filters, "NEW")


def extract_paid_invoices(fetcher: APIFetcher, status_list: list[str]) -> tuple[list[dict], dict[str, str]]:
    today = datetime.now()
    filters = {
        "data_pagamento_inicial": _fmt(today - timedelta(days=30)),
        "data_pagamento_final": _fmt(today),
    }
    logger.info(
        f"[PAID] Extracting by pagamento: {filters['data_pagamento_inicial']} "
        f"to {filters['data_pagamento_final']}"
    )
    return _extract_for_all_statuses(fetcher, status_list, filters, "PAID")


def extract_due_date_changes(fetcher: APIFetcher, status_list: list[str]) -> tuple[list[dict], dict[str, str]]:
    today = datetime.now()
    filters = {
        "data_vencimento_inicial": _fmt(today - timedelta(days=30)),
        "data_vencimento_final": _fmt(today + timedelta(days=30)),
    }
    logger.info(
        f"[DUE] Extracting by vencimento: {filters['data_vencimento_inicial']} "
        f"to {filters['data_vencimento_final']}"
    )
    return _extract_for_all_statuses(fetcher, status_list, filters, "DUE")


def merge_by_invoice(*batches: list[dict]) -> list[dict]:
    """Merges the windows on codigo_boleto; a later window wins on overlap.

    A record without codigo_boleto cannot be merged or loaded, and keying it
    under None would silently collapse all of them into one.
    """
    merged: dict[str, dict] = {}
    for batch in batches:
        for record in batch:
            key = record.get("codigo_boleto")
            if key is None:
                raise ValueError("An invoice arrived without codigo_boleto; refusing to merge the batch.")
            merged[str(key)] = record
    return list(merged.values())


def run_invoice_extraction() -> None:
    logger.info("Starting invoice daily extraction pipeline...")

    try:
        fetcher = build_invoice_fetcher(authenticate_user())
        status_list = get_invoice_statuses(fetcher)
        logger.info(f"Statuses found: {status_list}")

        new_records, new_failures = extract_new_invoices(fetcher, status_list)
        paid_records, paid_failures = extract_paid_invoices(fetcher, status_list)
        due_records, due_failures = extract_due_date_changes(fetcher, status_list)

        assert_extraction_complete({**new_failures, **paid_failures, **due_failures}, "invoices")

        all_records = merge_by_invoice(new_records, paid_records, due_records)

        logger.info(
            f"Extraction summary: {len(new_records)} new | {len(paid_records)} paid | "
            f"{len(due_records)} due-date | {len(all_records)} unique after dedup"
        )

        write_raw("invoices", INVOICE_ENDPOINT, all_records)

    except Exception as e:
        logger.error(f"Critical failure in the invoice daily extraction pipeline: {e}")
        raise


def run_invoice_backfill(start: date, end: date) -> None:
    """Re-extracts the invoices issued or paid in [start, end] as one raw batch.

    For nights the flow did not extract: the daily windows only look back 7
    days for new invoices and 30 for payments, so an invoice issued during a
    longer outage and not paid since is never seen. Lands a normal batch, which
    the next dbt build merges like any other. Run it outside the nightly window
    and follow it with a dbt build; the next nightly batch supersedes it.
    """
    if start > end:
        raise ValueError(f"Backfill start {start} is after end {end}.")
    logger.info(f"Starting invoice backfill for {start} to {end}...")

    fetcher = build_invoice_fetcher(authenticate_user())
    status_list = get_invoice_statuses(fetcher)
    first, last = start.strftime(FMT), end.strftime(FMT)

    issued, issued_failures = _extract_for_all_statuses(
        fetcher, status_list, {"data_emissao_inicial": first, "data_emissao_final": last}, "BACKFILL-NEW"
    )
    paid, paid_failures = _extract_for_all_statuses(
        fetcher, status_list, {"data_pagamento_inicial": first, "data_pagamento_final": last}, "BACKFILL-PAID"
    )
    assert_extraction_complete({**issued_failures, **paid_failures}, "invoices-backfill")

    all_records = merge_by_invoice(issued, paid)
    logger.info(f"Backfill summary: {len(issued)} issued | {len(paid)} paid | {len(all_records)} unique")
    write_raw("invoices", INVOICE_ENDPOINT, all_records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract invoices into raw.invoices.")
    parser.add_argument("--backfill", nargs=2, metavar=("START", "END"), type=date.fromisoformat,
                        help="re-extract invoices issued or paid between two ISO dates, inclusive")
    cli = parser.parse_args()
    if cli.backfill:
        run_invoice_backfill(*cli.backfill)
    else:
        run_invoice_extraction()
