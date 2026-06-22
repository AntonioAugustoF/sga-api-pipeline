import os
import json
import requests
from datetime import datetime
from infra.config import config
from infra.authenticator import authenticate_user
from infra.api_fetcher import APIFetcher, deduplicate_by_key
from infra.logger import get_logger

logger = get_logger(__name__)


def extract_customers_by_status(status_code, fetcher: APIFetcher) -> list[dict]:
    records = fetcher.fetch_by_offset(
        endpoint="/listar/associado",
        base_payload={"codigo_situacao": str(status_code)},
        offset_param="inicio_paginacao",
        page_size_param="quantidade_por_pagina",
        items_key="associados",
        total_key="total_associados",
    )
    for customer in records:
        customer["codigo_situacao"] = status_code
    logger.info(f"Status {status_code}: {len(records)} customers extracted.")
    return records


def run_customer_extraction() -> str:
    logger.info("Starting customer extraction pipeline...")

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

        status_lookup = {str(s["codigo_situacao"]): s["descricao_situacao"] for s in statuses_data}
        lookup_path = os.path.join("data", "raw", f"customers_status_lookup_{current_date}.json")
        with open(lookup_path, "w", encoding="utf-8") as f:
            json.dump(status_lookup, f, ensure_ascii=False, indent=2)
        logger.info(f"Status lookup saved to: {lookup_path}")

        all_records = []
        for status in status_list:
            try:
                all_records.extend(extract_customers_by_status(status, fetcher))
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 406:
                    logger.info(f"Status {status} not supported by /associado (406) — skipping.")
                else:
                    logger.warning(f"HTTP error extracting status {status}: {e}")
            except Exception as e:
                logger.warning(f"Error extracting status {status}: {e}")

        unique_customers = deduplicate_by_key(all_records, "codigo_associado")
        logger.info(f"Total extracted: {len(all_records)} | Unique: {len(unique_customers)}")

        output_path = os.path.join("data", "raw", f"customers_{current_date}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_customers, f, ensure_ascii=False, indent=2)

        logger.info(f"File successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Critical failure in the customer extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_customer_extraction()
