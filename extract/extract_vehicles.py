import os
import json
import requests
from datetime import datetime
from infra.config import config
from infra.authenticator import authenticate_user
from infra.api_fetcher import APIFetcher, deduplicate_by_key
from infra.logger import get_logger

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


def run_vehicle_extraction() -> str:
    logger.info("Starting vehicle extraction pipeline...")

    try:
        user_token = authenticate_user()
        current_date = datetime.now().strftime("%Y-%m-%d")
        fetcher = APIFetcher(config.API_BASE_URL, user_token, page_size=1000, timeout=60)

        url_statuses = f"{config.API_BASE_URL}/listar/situacao/todos"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {user_token}"
        }

        response = requests.get(url_statuses, headers=headers, timeout=60)
        response.raise_for_status()
        statuses_data = response.json()

        status_list = [s["codigo_situacao"] for s in statuses_data]
        logger.info(f"Statuses found to extract: {status_list}")

        all_records = []
        for status in status_list:
            try:
                all_records.extend(extract_vehicles_by_status(status, fetcher))
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 406:
                    logger.info(f"Status {status} not supported by /veiculo (406) — skipping.")
                else:
                    logger.warning(f"HTTP error extracting status {status}: {e}")
            except Exception as e:
                logger.warning(f"Error extracting status {status}: {e}")

        unique_vehicles = deduplicate_by_key(all_records, "codigo_veiculo")
        logger.info(f"Total extracted: {len(all_records)} | Unique: {len(unique_vehicles)}")

        output_path = os.path.join("data", "raw", f"vehicles_{current_date}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_vehicles, f, ensure_ascii=False, indent=2)

        logger.info(f"File successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Critical failure in the vehicle extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_vehicle_extraction()
