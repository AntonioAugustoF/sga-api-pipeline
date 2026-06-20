import requests

from infra.logger import get_logger
from infra.retry import with_retry

logger = get_logger(__name__)


class APIFetcher:
    """Encapsulates authenticated, paginated GET requests against the SGA API."""

    def __init__(self, base_url: str, user_token: str, page_size: int = 5000, timeout: int = 30):
        self._base_url = base_url
        self._user_token = user_token
        self._page_size = page_size
        self._timeout = timeout

    @property
    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._user_token}",
        }

    @with_retry()
    def _get_page(self, endpoint: str, payload: dict) -> requests.Response:
        url = f"{self._base_url}{endpoint}"
        response = requests.get(url, headers=self._headers, json=payload, timeout=self._timeout)
        response.raise_for_status()
        return response

    def fetch_by_page(self, endpoint: str, base_payload: dict, page_param: str, items_key: str) -> list[dict]:
        """Fetches all pages of a GET endpoint paginated by an incrementing page number."""
        page = 0
        records: list[dict] = []

        while True:
            payload = {**base_payload, page_param: page}
            response = self._get_page(endpoint, payload)
            data = response.json()

            items = data if isinstance(data, list) else data.get(items_key, [])
            if not items:
                break

            records.extend(items)
            logger.info(f"{endpoint} | Page {page}: {len(items)} records extracted.")

            if len(items) < self._page_size:
                break

            page += 1

        return records


def deduplicate_by_key(records: list[dict], key: str) -> list[dict]:
    """Removes records with a duplicate value for `key`, keeping first occurrence order."""
    seen = {}
    for record in records:
        record_id = record.get(key)
        if record_id not in seen:
            seen[record_id] = record
    return list(seen.values())
