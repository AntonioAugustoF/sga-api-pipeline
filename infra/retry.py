import functools
import time
from collections.abc import Callable
from typing import TypeVar

import requests

from infra.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def _is_retryable(e: requests.RequestException) -> bool:
    """
    Client errors (4xx) are not transient and should fail immediately;
    everything else (timeouts, connection drops, 5xx) is retried.
    """
    if isinstance(e, requests.HTTPError) and e.response is not None and 400 <= e.response.status_code < 500:
        return False
    return True


def with_retry(max_attempts: int = 5, backoff: float = 3.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retries the decorated function on transient requests.RequestException with exponential backoff.

    Defaults cover roughly two minutes (3+9+27+81s). The pipeline runs unattended
    overnight on a machine that may be waking from sleep, and the wireless link can
    take half a minute to reassociate — a shorter window turned routine reconnection
    into a failed extraction.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except requests.RequestException as e:
                    if not _is_retryable(e) or attempt == max_attempts:
                        if not _is_retryable(e):
                            logger.warning(f"{func.__name__} failed with non-retryable error: {e}")
                        else:
                            logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    wait = backoff ** attempt
                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {wait:.0f}s..."
                    )
                    time.sleep(wait)
        return wrapper
    return decorator
