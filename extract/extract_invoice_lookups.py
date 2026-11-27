"""Re-reads, one by one, the invoices the warehouse believes are open but the source no longer lists as open.

The daily invoice extraction only sees three windows (issued in the last 7
days, paid in the last 30, due within +-30 days). An invoice that leaves the
open status outside all three — typically a cancellation of an old or
far-future invoice — is never seen again, and fact_invoices keeps it 'aberto'
forever. On 2026-11-27 that was 1,082 invoices, checked against the API: they
had been cancelled.

The delinquency extraction is the full list of open invoices, so the set to
re-read is exact and small: open in the fact, absent from today's delinquency
batch. /buscar/boleto/{nosso_numero} answers for one invoice with its current
state; dbt applies only the status and payment fields from it
(stg_sga__invoice_lookups), because its payload shape differs from the listing.

Must run after the delinquency extraction of the same run: the candidate set
is computed against the latest raw.delinquency batch.
"""

import time
from collections.abc import Callable

import requests
from sqlalchemy import text

from infra.api_fetcher import APIFetcher
from infra.authenticator import authenticate_user
from infra.config import config
from infra.db_connector import get_db_engine
from infra.extraction_guard import PartialExtractionError, assert_extraction_complete
from infra.logger import get_logger
from infra.raw_writer import write_raw

logger = get_logger(__name__)

LOOKUP_ENDPOINT = "/buscar/boleto"

# The API blocks the account when called too fast, and the block covers every
# endpoint including authentication — so it takes the whole nightly run down,
# not just this step. Measured on 2026-11-27: ~390 lookups at ~2.2 requests/s
# with four workers, then 403 on everything, /usuario/autenticar included.
# Hence one request at a time, spaced, and a nightly budget: a backlog drains
# over several nights instead of in one burst.
SECONDS_BETWEEN_LOOKUPS = 2.0
MAX_LOOKUPS_PER_RUN = 150

# A candidate set far above any plausible backlog means the comparison itself
# is broken — most likely a truncated delinquency batch.
MAX_CANDIDATES = 5000


class SourceRefusedError(RuntimeError):
    """Raised when the API answers 403: stop calling it at once.

    Carries the records read before the refusal, which are still worth landing.
    """

    def __init__(self, message: str, records: list[dict]) -> None:
        super().__init__(message)
        self.records = records


# Fields the lookup returns that the warehouse never uses and that identify or
# let someone pay on behalf of a person. Not landing them is data minimisation:
# raw is otherwise kept untouched, but nothing downstream reads these.
DROPPED_FIELDS = ("email", "pix", "linha_digitavel", "link_boleto", "short_link")

CANDIDATES_SQL = text(
    """
    with latest_delinquency as (
        select payload ->> 'codigo_boleto' as codigo_boleto
        from raw.delinquency
        where _extracted_at = (select max(_extracted_at) from raw.delinquency)
    )
    select f.codigo_boleto, f.nosso_numero
    from analytics.fact_invoices_base f
    where f.codigo_situacao_boleto = '2'
      and f.nosso_numero is not null
      and not exists (select 1 from latest_delinquency d where d.codigo_boleto = f.codigo_boleto)
    order by f.codigo_boleto
    """
)


def find_candidates() -> dict[str, str]:
    """Returns {nosso_numero: codigo_boleto} for every invoice to re-read."""
    with get_db_engine().connect() as conn:
        if conn.execute(text("select to_regclass('analytics.fact_invoices_base')")).scalar() is None:
            logger.info("analytics.fact_invoices_base does not exist yet; nothing to reconcile.")
            return {}
        rows = conn.execute(CANDIDATES_SQL).all()
    return {str(nosso_numero): str(codigo_boleto) for codigo_boleto, nosso_numero in rows}


def _minimise(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in DROPPED_FIELDS}


def lookup_invoices(
    fetcher: APIFetcher,
    candidates: dict[str, str],
    interval_seconds: float = SECONDS_BETWEEN_LOOKUPS,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[list[dict], list[str], dict[str, str]]:
    """Fetches each candidate, one at a time. Returns (records, not_found, failures).

    A 403 ends the loop immediately with SourceRefusedError: every further call
    would be refused too, and keeps the block in place for longer.
    """
    records: list[dict] = []
    not_found: list[str] = []
    failures: dict[str, str] = {}

    for index, (nosso_numero, expected) in enumerate(candidates.items()):
        if index:
            sleep(interval_seconds)
        try:
            record = fetcher.fetch_one(f"{LOOKUP_ENDPOINT}/{nosso_numero}")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                raise SourceRefusedError(
                    f"The API refused lookup {index + 1} of {len(candidates)} with 403; stopped calling it. "
                    "The account is probably rate-limited.",
                    records,
                ) from e
            failures[nosso_numero] = str(e)
            continue
        except Exception as e:
            failures[nosso_numero] = str(e)
            continue
        if record is None:
            not_found.append(expected)
            continue
        if str(record.get("codigo_boleto")) != expected:
            failures[nosso_numero] = f"lookup returned codigo_boleto {record.get('codigo_boleto')}, expected {expected}"
            continue
        records.append(_minimise(record))

    return records, not_found, failures


def run_invoice_lookup_extraction() -> None:
    logger.info("Starting invoice status reconciliation...")

    try:
        candidates = find_candidates()
        if not candidates:
            logger.info("No open invoice is missing from the delinquency batch; nothing to reconcile.")
            return
        if len(candidates) > MAX_CANDIDATES:
            raise PartialExtractionError(
                f"{len(candidates)} open invoices are missing from the latest delinquency batch, above the "
                f"{MAX_CANDIDATES} limit. The delinquency extraction is probably incomplete."
            )

        backlog = len(candidates)
        # Oldest codigo_boleto first (the query orders by it), so a backlog
        # drains in a stable order across nights.
        candidates = dict(list(candidates.items())[:MAX_LOOKUPS_PER_RUN])
        logger.info(
            f"{backlog} open invoices missing from the delinquency batch; re-reading {len(candidates)} "
            f"tonight ({backlog - len(candidates)} left for later nights)."
        )
        fetcher = APIFetcher(config.API_BASE_URL, authenticate_user(), timeout=60)
        try:
            records, not_found, failures = lookup_invoices(fetcher, candidates)
        except SourceRefusedError as e:
            # Unlike a listing, each lookup is an independent correction, not a
            # slice of a snapshot: what was read before the refusal is complete
            # for those invoices, so it lands, and the run still fails.
            if e.records:
                write_raw("invoice_lookups", LOOKUP_ENDPOINT, e.records)
            raise

        # Same reasoning: land the lookups that succeeded, then fail loudly
        # over the ones that did not.
        if records:
            write_raw("invoice_lookups", LOOKUP_ENDPOINT, records)
        assert_extraction_complete(failures, "invoice_lookups")

        if not_found:
            # Not an extraction failure: the API no longer has the invoice at all.
            # It stays 'aberto' in the fact, and
            # assert_open_invoices_are_in_delinquency keeps reporting it.
            logger.warning(f"{len(not_found)} invoices no longer exist in the source: {sorted(not_found)[:20]}")

        logger.info(f"Reconciliation: {len(records)} re-read | {len(not_found)} not found.")

    except Exception as e:
        logger.error(f"Critical failure in invoice status reconciliation: {e}")
        raise


if __name__ == "__main__":
    run_invoice_lookup_extraction()
