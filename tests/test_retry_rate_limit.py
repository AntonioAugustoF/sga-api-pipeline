from unittest.mock import MagicMock

import pytest
import requests

from infra.retry import with_retry


def _http_error(status_code: int, headers: dict) -> requests.HTTPError:
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers
    error = requests.HTTPError(f"{status_code} error")
    error.response = response
    return error


def _flaky(status_code: int, headers: dict, failures: int):
    calls = {"n": 0}

    @with_retry(max_attempts=3, backoff=0.001)
    def call():
        calls["n"] += 1
        if calls["n"] <= failures:
            raise _http_error(status_code, headers)
        return "ok"

    return call, calls


def test_rate_limiting_is_retried(monkeypatch):
    """429 is a 4xx that asks to be called again, not a malformed request."""
    monkeypatch.setattr("infra.retry.time.sleep", lambda s: None)
    call, calls = _flaky(429, {}, failures=1)
    assert call() == "ok"
    assert calls["n"] == 2


def test_retry_after_sets_a_floor_on_the_wait(monkeypatch):
    waits: list[float] = []
    monkeypatch.setattr("infra.retry.time.sleep", waits.append)
    call, _ = _flaky(429, {"Retry-After": "12"}, failures=1)
    assert call() == "ok"
    assert waits[0] >= 12


def test_an_unreasonable_retry_after_fails_instead_of_sleeping(monkeypatch):
    monkeypatch.setattr("infra.retry.time.sleep", lambda s: pytest.fail("must not sleep"))
    call, calls = _flaky(429, {"Retry-After": "3600"}, failures=5)
    with pytest.raises(requests.HTTPError):
        call()
    assert calls["n"] == 1
