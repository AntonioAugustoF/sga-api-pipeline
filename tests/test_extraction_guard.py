import pytest

from infra.extraction_guard import PartialExtractionError, assert_extraction_complete


def test_allows_a_complete_extraction():
    assert_extraction_complete({}, "vehicles")


def test_raises_when_any_status_failed():
    with pytest.raises(PartialExtractionError, match="vehicles"):
        assert_extraction_complete({"2": "ConnectionError"}, "vehicles")


def test_message_names_every_failing_status():
    """Diagnosing the run requires which statuses are missing, not how many."""
    failures = {"2": "ConnectionError", "17": "ReadTimeout"}

    with pytest.raises(PartialExtractionError) as excinfo:
        assert_extraction_complete(failures, "vehicles")

    message = str(excinfo.value)
    assert "2: ConnectionError" in message
    assert "17: ReadTimeout" in message
    assert "2 status(es)" in message


def test_error_is_a_runtime_error():
    """The extractores re-raise from a bare `except Exception`, and the flow must fail."""
    assert issubclass(PartialExtractionError, RuntimeError)