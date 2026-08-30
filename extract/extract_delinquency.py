from extract.extract_invoices import _fetch_by_status
from infra.authenticator import authenticate_user
from infra.logger import get_logger
from infra.raw_writer import write_raw

logger = get_logger(__name__)

DELINQUENCY_STATUS = 2


def run_delinquency_extraction() -> None:
    logger.info("Starting delinquency extraction (status=2, no date filter)...")

    try:
        user_token = authenticate_user()
        records = _fetch_by_status(DELINQUENCY_STATUS, user_token, date_filters={})

        logger.info(f"Total open invoices extracted: {len(records)}")

        write_raw("delinquency", "/listar/boleto?codigo_situacao=2", records)

    except Exception as e:
        logger.error(f"Critical failure in delinquency extraction: {e}")
        raise


if __name__ == "__main__":
    run_delinquency_extraction()
