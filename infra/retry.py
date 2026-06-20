import functools
import time
from typing import Callable, TypeVar

import requests

from infra.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def with_retry(max_attempts: int = 3, backoff: float = 2.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retries the decorated function on requests.RequestException with exponential backoff."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except requests.RequestException as e:
                    if attempt == max_attempts:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    wait = backoff ** attempt
                    logger.warning(f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. Retrying in {wait:.0f}s...")
                    time.sleep(wait)
        return wrapper
    return decorator
