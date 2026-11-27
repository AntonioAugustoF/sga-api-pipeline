import requests

from infra.extraction_guard import PartialExtractionError
from infra.logger import get_logger
from infra.retry import with_retry

logger = get_logger(__name__)

# The SGA API answers 406 when a query matches nothing: an empty result set,
# not an unsupported request. Past the last page of a page-numbered endpoint it
# answers the same way, which is why the code must be read in context.
EMPTY_RESULT_STATUS = 406


class IncompletePaginationError(PartialExtractionError):
    """Raised when pagination ended with fewer records than the server announced."""


def _is_empty_result(e: requests.HTTPError) -> bool:
    return e.response is not None and e.response.status_code == EMPTY_RESULT_STATUS


class APIFetcher:
    """Encapsulates authenticated, paginated requests against the SGA API.

    The API paginates in two incompatible ways, both through a parameter named
    `inicio_paginacao`, and both were verified against the live API:

    * /listar/associado and /listar/veiculo read it as a record offset
      (start=1 returns records 2..101 of a 100-sized page) -> fetch_by_offset.
    * /listar/boleto reads it as a page number (start=1 returns records
      101..200) and returns a bare list without a total -> fetch_by_page_number.
    """

    def __init__(self, base_url: str, user_token: str, page_size: int = 5000, timeout: int = 30) -> None:
        self._base_url = base_url
        self._user_token = user_token
        self._page_size = page_size
        self._timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._user_token}",
        }

    # The body is parsed inside the retried call. A non-JSON answer (a gateway
    # or maintenance page served with 200) raises requests' JSONDecodeError, a
    # RequestException, and is transient in practice: the volunteer endpoint did
    # it on three consecutive nights in 2026-11, and parsing outside the retry
    # turned each one into a failed status on the first attempt.
    @with_retry()
    def _get_page(self, endpoint: str, payload: dict) -> list | dict:
        url = f"{self._base_url}{endpoint}"
        response = requests.get(url, headers=self._headers, json=payload, timeout=self._timeout)
        response.raise_for_status()
        return response.json()

    @with_retry()
    def _post_page(self, endpoint: str, payload: dict) -> list | dict:
        url = f"{self._base_url}{endpoint}"
        response = requests.post(url, headers=self._headers, json=payload, timeout=self._timeout)
        response.raise_for_status()
        return response.json()

    @with_retry()
    def fetch_all(self, endpoint: str) -> list[dict] | dict:
        """Fetches an unpaginated reference list in a single request.

        Status lists arrive whole, so the pagination helpers don't apply — but the
        call still needs the retry, headers and timeout the fetcher already carries.
        """
        url = f"{self._base_url}{endpoint}"
        response = requests.get(url, headers=self._headers, timeout=self._timeout)
        response.raise_for_status()
        return response.json()

    def fetch_one(self, endpoint: str) -> dict | None:
        """GETs a single record. Returns None when the API answers 406 (not found)."""
        try:
            return self.fetch_all(endpoint)
        except requests.HTTPError as e:
            if _is_empty_result(e):
                return None
            raise

    def fetch_by_offset(
        self,
        endpoint: str,
        base_payload: dict,
        offset_param: str,
        page_size_param: str,
        items_key: str,
        total_key: str,
    ) -> list[dict]:
        """Fetches all pages of a POST endpoint paginated by an incrementing record offset.

        Raises IncompletePaginationError when the loop ends below the total the
        server announced: a short page in the middle of a listing used to end the
        loop and pass as a complete extraction.
        """
        payload = {**base_payload, page_size_param: self._page_size, offset_param: 0}
        records: list[dict] = []
        total = None

        while True:
            data = self._post_page(endpoint, payload)

            if total is None:
                total = data.get(total_key)

            items = data.get(items_key, [])
            if not items:
                break

            records.extend(items)
            logger.info(f"{endpoint} | Offset {payload[offset_param]}: {len(items)} records extracted.")

            payload[offset_param] += self._page_size

            if len(items) < self._page_size or (total is not None and len(records) >= int(total)):
                break

        _assert_reached_total(endpoint, base_payload, records, total)
        return records

    def fetch_by_page_number(
        self,
        endpoint: str,
        base_payload: dict,
        page_param: str,
        page_size_param: str,
        items_key: str,
        total_key: str,
    ) -> list[dict]:
        """Fetches all pages of a POST endpoint paginated by page number (0-based).

        A 406 on the first page is an empty result; on a later page it is the end
        of the listing — reached whenever the record count is an exact multiple
        of the page size. Treating that second case as an error used to discard
        every page already read for the status.
        """
        page = 0
        records: list[dict] = []
        total = None

        while True:
            payload = {**base_payload, page_size_param: self._page_size, page_param: page}
            try:
                data = self._post_page(endpoint, payload)
            except requests.HTTPError as e:
                if _is_empty_result(e):
                    break
                raise

            if isinstance(data, list):
                items = data
            else:
                if total is None:
                    total = data.get(total_key)
                items = data.get(items_key, [])

            if not items:
                break

            records.extend(items)
            logger.info(f"{endpoint} | Page {page}: {len(items)} records extracted.")

            if len(items) < self._page_size or (total is not None and len(records) >= int(total)):
                break

            page += 1

        _assert_reached_total(endpoint, base_payload, records, total)
        return records

    def fetch_by_page(self, endpoint: str, base_payload: dict, page_param: str, items_key: str) -> list[dict]:
        """Fetches all pages of a GET endpoint paginated by an incrementing page number."""
        page = 0
        records: list[dict] = []

        while True:
            payload = {**base_payload, page_param: page}
            data = self._get_page(endpoint, payload)

            items = data if isinstance(data, list) else data.get(items_key, [])
            if not items:
                break

            records.extend(items)
            logger.info(f"{endpoint} | Page {page}: {len(items)} records extracted.")

            if len(items) < self._page_size:
                break

            page += 1

        return records


def _assert_reached_total(endpoint: str, base_payload: dict, records: list[dict], total: object) -> None:
    if total is None:
        return
    expected = int(total)
    if len(records) < expected:
        raise IncompletePaginationError(
            f"{endpoint} {base_payload}: pagination ended with {len(records)} of the "
            f"{expected} records the server announced."
        )


def deduplicate_by_key(records: list[dict], key: str) -> list[dict]:
    """Removes records with a duplicate value for `key`, keeping first occurrence order.

    Raises when a record lacks the key: keyed under None, every such record would
    collapse into one, and a renamed field in the API would land a one-row batch
    that write_raw has no way to tell from a real one.
    """
    seen: dict[object, dict] = {}
    for record in records:
        record_id = record.get(key)
        if record_id is None:
            raise ValueError(f"A record arrived without '{key}'; refusing to deduplicate the batch.")
        if record_id not in seen:
            seen[record_id] = record
    return list(seen.values())
