from infra.api_fetcher import APIFetcher
from infra.authenticator import authenticate_user
from infra.config import config
from infra.logger import get_logger
from infra.raw_writer import write_raw

logger = get_logger(__name__)

# Both endpoints return the full reference list in a single unpaginated response,
# so APIFetcher's pagination helpers don't apply here.
STATUS_DOMAINS = {
    "statuses": "/listar/situacao/todos",
    "invoice_statuses": "/listar/situacao-boleto/todos",
}


def run_status_extraction() -> None:
    """Lands both status reference lists (registration and invoice) in raw.

    These lists are filtered by the API user's permissions, so a status the user
    cannot see is simply absent from the response — no error is raised. Persisting
    them lets the load step detect newly granted codes and flag the coverage change.
    """
    logger.info("Starting status extraction pipeline...")

    try:
        user_token = authenticate_user()
        fetcher = APIFetcher(config.API_BASE_URL, user_token, timeout=60)

        for entity, endpoint in STATUS_DOMAINS.items():
            records = fetcher.fetch_all(endpoint)
            logger.info(f"{entity}: {len(records)} statuses extracted from {endpoint}.")

            write_raw(entity, endpoint, records)

    except Exception as e:
        logger.error(f"Critical failure in the status extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_status_extraction()
