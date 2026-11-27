from infra.api_fetcher import APIFetcher, deduplicate_by_key
from infra.authenticator import authenticate_user
from infra.config import config
from infra.extraction_guard import assert_extraction_complete
from infra.logger import get_logger
from infra.raw_writer import write_raw

logger = get_logger(__name__)

TARGET_STATUSES = ["ativo", "inativo"]


def extract_regionals_by_status(status_name: str, fetcher: APIFetcher) -> list[dict]:
    records = fetcher.fetch_by_page(
        endpoint="/listar/regional/ativo",
        base_payload={"situacao": status_name},
        page_param="pagina",
        items_key="regionais",
    )
    for regional in records:
        regional["situacao_origem"] = status_name
    return records


def run_regional_extraction() -> None:
    logger.info("Starting regional extraction pipeline...")

    try:
        user_token = authenticate_user()
        fetcher = APIFetcher(config.API_BASE_URL, user_token)

        all_records: list[dict] = []
        failures: dict[str, str] = {}
        for status in TARGET_STATUSES:
            try:
                all_records.extend(extract_regionals_by_status(status, fetcher))
            except Exception as e:
                logger.warning(f"Error extracting regionals for status {status}: {e}")
                failures[status] = str(e)

        # Both statuses land every night; one missing would silently drop every
        # regional in it from the dimension.
        assert_extraction_complete(failures, "regionals")

        unique_regionals = deduplicate_by_key(all_records, "codigo_regional")
        logger.info(f"Total extracted: {len(all_records)} | Unique: {len(unique_regionals)}")

        write_raw("regionals", "/listar/regional/ativo", unique_regionals)

    except Exception as e:
        logger.error(f"Critical failure in the regional extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_regional_extraction()
