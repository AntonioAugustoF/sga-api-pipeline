import os
import json
from datetime import datetime
from infra.config import config
from infra.authenticator import authenticate_user
from infra.api_fetcher import APIFetcher, deduplicate_by_key
from infra.logger import get_logger

logger = get_logger(__name__)

TARGET_STATUSES = ["ativo", "inativo"]


def extract_cooperatives_by_status(status_name: str, fetcher: APIFetcher) -> list[dict]:
    records = fetcher.fetch_by_page(
        endpoint="/listar/cooperativa/ativo",
        base_payload={"situacao": status_name},
        page_param="pagina",
        items_key="cooperativas",
    )
    for cooperative in records:
        cooperative["situacao_origem"] = status_name
    return records


def run_cooperative_extraction() -> str:
    logger.info("Starting cooperative extraction pipeline...")

    try:
        user_token = authenticate_user()
        fetcher = APIFetcher(config.API_BASE_URL, user_token)

        all_records = []
        for status in TARGET_STATUSES:
            try:
                all_records.extend(extract_cooperatives_by_status(status, fetcher))
            except Exception as e:
                logger.warning(f"Error extracting cooperatives for status {status}: {e}")

        unique_cooperatives = deduplicate_by_key(all_records, "codigo_cooperativa")
        logger.info(f"Total extracted: {len(all_records)} | Unique: {len(unique_cooperatives)}")

        current_date = datetime.now().strftime("%Y-%m-%d")
        output_path = os.path.join("data", "raw", f"cooperatives_{current_date}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_cooperatives, f, ensure_ascii=False, indent=2)

        logger.info(f"File successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Critical failure in the cooperative extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_cooperative_extraction()
