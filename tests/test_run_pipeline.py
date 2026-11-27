import pytest

from orchestrators.run_pipeline import ExtractionFailedError, _raise_if_failed


class _State:
    def __init__(self, failed: bool = False, crashed: bool = False) -> None:
        self._failed, self._crashed = failed, crashed

    def is_failed(self) -> bool:
        return self._failed

    def is_crashed(self) -> bool:
        return self._crashed


def test_dbt_is_blocked_when_any_extraction_failed():
    states = {"vehicles": _State(), "invoices": _State(failed=True), "customers": _State(crashed=True)}
    with pytest.raises(ExtractionFailedError, match="2 extraction"):
        _raise_if_failed(states)


def test_nothing_is_raised_when_every_extraction_landed():
    _raise_if_failed({"vehicles": _State(), "invoices": _State()})
