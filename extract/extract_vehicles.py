import requests

from infra.api_fetcher import APIFetcher, deduplicate_by_key
from infra.authenticator import authenticate_user
from infra.config import config
from infra.extraction_guard import assert_extraction_complete
from infra.logger import get_logger
from infra.raw_writer import write_raw

logger = get_logger(__name__)


def extract_vehicles_by_status(status_code, fetcher: APIFetcher) -> list[dict]:
    records = fetcher.fetch_by_offset(
        endpoint="/listar/veiculo",
        base_payload={"codigo_situacao": str(status_code)},
        offset_param="inicio_paginacao",
        page_size_param="quantidade_por_pagina",
        items_key="veiculos",
        total_key="total_veiculos",
    )
    for vehicle in records:
        vehicle["codigo_situacao"] = status_code
    logger.info(f"Status {status_code}: {len(records)} vehicles extracted.")
    return records


def run_vehicle_extraction() -> None:
    logger.info("Starting vehicle extraction pipeline...")

    try:
        user_token = authenticate_user()
        fetcher = APIFetcher(config.API_BASE_URL, user_token, page_size=1000, timeout=60)

        statuses_data = fetcher.fetch_all("/listar/situacao/todos")

        status_list = [s["codigo_situacao"] for s in statuses_data]
        logger.info(f"Statuses found to extract: {status_list}")

        all_records = []
        failures: dict[str, str] = {}
        for status in status_list:
            try:
                all_records.extend(extract_vehicles_by_status(status, fetcher))
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 406:
                    # The API answers 406 with "no vehicles found for the given
                    # parameters": an empty result set, not an unsupported status.
                    logger.info(f"Status {status}: no vehicles found (406 empty result).")
                else:
                    logger.warning(f"HTTP error extracting status {status}: {e}")
                    failures[str(status)] = str(e)
            except Exception as e:
                logger.warning(f"Error extracting status {status}: {e}")
                failures[str(status)] = str(e)

        assert_extraction_complete(failures, "vehicles")

        unique_vehicles = deduplicate_by_key(all_records, "codigo_veiculo")
        logger.info(f"Total extracted: {len(all_records)} | Unique: {len(unique_vehicles)}")

        write_raw("vehicles", "/listar/veiculo", unique_vehicles)

    except Exception as e:
        logger.error(f"Critical failure in the vehicle extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_vehicle_extraction()
