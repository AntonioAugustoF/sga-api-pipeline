import requests
import pytest

from infra.retry import with_retry


def test_with_retry_returns_result_on_eventual_success():
    calls = {"n": 0}

    @with_retry(max_attempts=3, backoff=0.001)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.ConnectionError("boom")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_with_retry_raises_after_max_attempts():
    calls = {"n": 0}

    @with_retry(max_attempts=2, backoff=0.001)
    def always_fails():
        calls["n"] += 1
        raise requests.ConnectionError("boom")

    with pytest.raises(requests.ConnectionError):
        always_fails()

    assert calls["n"] == 2


def test_with_retry_does_not_retry_other_exceptions():
    calls = {"n": 0}

    @with_retry(max_attempts=3, backoff=0.001)
    def raises_value_error():
        calls["n"] += 1
        raise ValueError("not a network error")

    with pytest.raises(ValueError):
        raises_value_error()

    assert calls["n"] == 1
