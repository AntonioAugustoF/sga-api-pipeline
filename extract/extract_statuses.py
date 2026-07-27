import os
import json
import requests
from datetime import datetime
from infra.config import config
from infra.authenticator import authenticate_user
from infra.logger import get_logger
from infra.retry import with_retry

logger = get_logger(__name__)

# Both endpoints return the full reference list in a single unpaginated response,
# so APIFetcher's pagination helpers don't apply here.
STATUS_DOMAINS = {
    "statuses": "/listar/situacao/todos",
    "invoice_statuses": "/listar/situacao-boleto/todos",
}


@with_retry()
def _get_statuses(endpoint: str, headers: dict) -> list[dict]:
    response = requests.get(f"{config.API_BASE_URL}{endpoint}", headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()


def run_status_extraction() -> list[str]:
    """Extracts both status reference lists (registration and invoice) to data/raw.

    These lists are filtered by the API user's permissions, so a status the user
    cannot see is simply absent from the response — no error is raised. Persisting
    them lets the load step detect newly granted codes and flag the coverage change.
    """
    logger.info("Starting status extraction pipeline...")

    try:
        user_token = authenticate_user()
        current_date = datetime.now().strftime("%Y-%m-%d")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {user_token}"
        }

        output_paths = []
        for entity, endpoint in STATUS_DOMAINS.items():
            records = _get_statuses(endpoint, headers)
            logger.info(f"{entity}: {len(records)} statuses extracted from {endpoint}.")

            output_path = os.path.join("data", "raw", f"{entity}_{current_date}.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)

            logger.info(f"File successfully saved to: {output_path}")
            output_paths.append(output_path)

        return output_paths

    except Exception as e:
        logger.error(f"Critical failure in the status extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_status_extraction()
