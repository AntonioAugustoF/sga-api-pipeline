from unittest.mock import MagicMock

import pytest
import requests

from extract.extract_invoice_lookups import DROPPED_FIELDS, SourceRefusedError, lookup_invoices


class _FakeFetcher:
    def __init__(self, answers: dict) -> None:
        self._answers = answers

    def fetch_one(self, endpoint: str) -> dict | None:
        answer = self._answers[endpoint.rsplit("/", 1)[-1]]
        if isinstance(answer, Exception):
            raise answer
        return answer


def test_lookup_separates_records_missing_invoices_and_failures():
    fetcher = _FakeFetcher(
        {
            "100": {"codigo_boleto": "1", "codigo_situacao_boleto": "3"},
            "200": None,
            "300": {"codigo_boleto": "999"},
            "400": RuntimeError("timeout"),
        }
    )
    candidates = {"100": "1", "200": "2", "300": "3", "400": "4"}

    records, not_found, failures = lookup_invoices(fetcher, candidates, interval_seconds=0)

    assert records == [{"codigo_boleto": "1", "codigo_situacao_boleto": "3"}]
    assert not_found == ["2"]
    assert set(failures) == {"300", "400"}
    assert "expected 3" in failures["300"]


def test_contact_and_payment_link_fields_are_not_landed():
    fetcher = _FakeFetcher({"1": {"codigo_boleto": "9", **dict.fromkeys(DROPPED_FIELDS, "x")}})
    records, _, _ = lookup_invoices(fetcher, {"1": "9"}, interval_seconds=0)
    assert records == [{"codigo_boleto": "9"}]


def _forbidden() -> requests.HTTPError:
    response = MagicMock()
    response.status_code = 403
    return requests.HTTPError("403", response=response)


def test_a_403_stops_every_further_call():
    """The block covers authentication too; hammering on keeps it in place."""
    calls: list[str] = []

    class _Refusing:
        def fetch_one(self, endpoint: str) -> dict | None:
            calls.append(endpoint)
            raise _forbidden()

    with pytest.raises(SourceRefusedError, match="lookup 1 of 3"):
        lookup_invoices(_Refusing(), {"1": "a", "2": "b", "3": "c"}, interval_seconds=0)
    assert len(calls) == 1


def test_lookups_are_spaced():
    waits: list[float] = []
    fetcher = _FakeFetcher({"1": None, "2": None, "3": None})
    lookup_invoices(fetcher, {"1": "a", "2": "b", "3": "c"}, interval_seconds=2.0, sleep=waits.append)
    assert waits == [2.0, 2.0]
