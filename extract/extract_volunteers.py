import os
import json
from datetime import datetime
from infra.config import config
from infra.authenticator import authenticate_user
from infra.api_fetcher import APIFetcher, deduplicate_by_key
from infra.logger import get_logger

logger = get_logger(__name__)

TARGET_STATUSES = ["ativo", "inativo"]


def extract_volunteers_by_status(status_name: str, fetcher: APIFetcher) -> list[dict]:
    records = fetcher.fetch_by_page(
        endpoint=f"/listar/voluntario/{status_name}",
        base_payload={"situacao": status_name},
        page_param="pagina",
        items_key="voluntarios",
    )
    for volunteer in records:
        volunteer["situacao_origem"] = status_name
    return records


def run_volunteer_extraction() -> str:
    logger.info("Starting volunteer extraction pipeline...")

    try:
        user_token = authenticate_user()
        fetcher = APIFetcher(config.API_BASE_URL, user_token)

        all_records = []
        for status in TARGET_STATUSES:
            try:
                all_records.extend(extract_volunteers_by_status(status, fetcher))
            except Exception as e:
                logger.warning(f"Error extracting volunteers for status {status}: {e}")

        unique_volunteers = deduplicate_by_key(all_records, "codigo_voluntario")
        logger.info(f"Total extracted: {len(all_records)} | Unique: {len(unique_volunteers)}")

        current_date = datetime.now().strftime("%Y-%m-%d")
        output_path = os.path.join("data", "raw", f"volunteers_{current_date}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_volunteers, f, ensure_ascii=False, indent=2)

        logger.info(f"File successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Critical failure in the volunteer extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_volunteer_extraction()
