import functools
import random
import time
from collections.abc import Callable
from typing import TypeVar

import requests

from infra.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# 429 is the one client error that is transient by definition: the server is
# asking to be called again later, not saying the request is wrong.
RETRYABLE_CLIENT_ERRORS = frozenset({408, 429})

# A Retry-After longer than this is treated as a refusal rather than honoured:
# sleeping for an hour inside a nightly run is worse than failing loudly.
MAX_RETRY_AFTER_SECONDS = 300.0


def _status_code(e: requests.RequestException) -> int | None:
    if isinstance(e, requests.HTTPError) and e.response is not None:
        return e.response.status_code
    return None


def _is_retryable(e: requests.RequestException) -> bool:
    """
    Client errors (4xx) are not transient and should fail immediately, except
    408 and 429; everything else (timeouts, connection drops, 5xx) is retried.
    """
    status = _status_code(e)
    if status is not None and 400 <= status < 500 and status not in RETRYABLE_CLIENT_ERRORS:
        return False
    return True


def _retry_after_seconds(e: requests.RequestException) -> float | None:
    """Reads a numeric Retry-After header, if the server sent one."""
    if not isinstance(e, requests.HTTPError) or e.response is None:
        return None
    headers = getattr(e.response, "headers", None) or {}
    value = headers.get("Retry-After") if hasattr(headers, "get") else None
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def with_retry(max_attempts: int = 5, backoff: float = 3.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retries the decorated function on transient requests.RequestException with exponential backoff.

    Defaults cover roughly two minutes (3+9+27+81s). The pipeline runs unattended
    overnight on a machine that may be waking from sleep, and the wireless link can
    take half a minute to reassociate — a shorter window turned routine reconnection
    into a failed extraction.

    Each wait carries up to 25% of random jitter, so parallel callers that failed
    together do not retry in lockstep. A Retry-After header, when present, sets a
    floor on the wait.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except requests.RequestException as e:
                    retryable = _is_retryable(e)
                    if not retryable or attempt == max_attempts:
                        if not retryable:
                            logger.warning(f"{func.__name__} failed with non-retryable error: {e}")
                        else:
                            logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise

                    wait = backoff**attempt
                    wait += random.uniform(0, wait * 0.25)
                    retry_after = _retry_after_seconds(e)
                    if retry_after is not None:
                        if retry_after > MAX_RETRY_AFTER_SECONDS:
                            logger.error(f"{func.__name__}: server asked to wait {retry_after:.0f}s; giving up.")
                            raise
                        wait = max(wait, retry_after)

                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {wait:.0f}s..."
                    )
                    time.sleep(wait)
            raise AssertionError("unreachable")  # pragma: no cover

        return wrapper

    return decorator
