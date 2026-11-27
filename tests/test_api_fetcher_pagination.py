from unittest.mock import MagicMock, patch

import pytest
import requests

from infra.api_fetcher import APIFetcher, IncompletePaginationError, deduplicate_by_key
from infra.extraction_guard import PartialExtractionError


def _ok(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _http_error(status_code: int):
    response = MagicMock()
    response.status_code = status_code
    response.raise_for_status.side_effect = requests.HTTPError(f"{status_code}", response=response)
    return response


def _page_number_fetch(responses, page_size=2):
    with patch("requests.post", side_effect=responses) as mock_post:
        fetcher = APIFetcher("http://fake", "token", page_size=page_size)
        records = fetcher.fetch_by_page_number(
            "/listar/boleto",
            {"codigo_situacao": 2},
            "inicio_paginacao",
            "quantidade_por_pagina",
            "boletos",
            "total_boletos",
        )
    return records, mock_post


def test_fetch_by_offset_raises_when_pagination_ends_below_the_announced_total():
    """A short page in the middle of a listing used to pass as a complete extraction."""
    responses = [_ok({"total_associados": 5, "associados": [{"codigo_associado": 1}]})]
    with patch("requests.post", side_effect=responses), pytest.raises(IncompletePaginationError, match="1 of the 5"):
        APIFetcher("http://fake", "token", page_size=2).fetch_by_offset(
            "/listar/associado",
            {"codigo_situacao": "1"},
            "inicio_paginacao",
            "quantidade_por_pagina",
            "associados",
            "total_associados",
        )


def test_incomplete_pagination_is_a_partial_extraction():
    """So the per-status loops record it as a failure and the guard refuses the batch."""
    assert issubclass(IncompletePaginationError, PartialExtractionError)


def test_fetch_by_page_number_increments_the_page_not_the_offset():
    responses = [_ok([{"codigo_boleto": "1"}, {"codigo_boleto": "2"}]), _ok([{"codigo_boleto": "3"}])]
    records, mock_post = _page_number_fetch(responses)
    assert [r["codigo_boleto"] for r in records] == ["1", "2", "3"]
    assert [c.kwargs["json"]["inicio_paginacao"] for c in mock_post.call_args_list] == [0, 1]


def test_a_406_past_the_last_full_page_ends_the_listing_and_keeps_what_was_read():
    """With a record count that is an exact multiple of the page size the API
    answers the next page with 406, which used to discard the whole status."""
    responses = [_ok([{"codigo_boleto": "1"}, {"codigo_boleto": "2"}]), _http_error(406)]
    records, _ = _page_number_fetch(responses)
    assert [r["codigo_boleto"] for r in records] == ["1", "2"]


def test_a_406_on_the_first_page_is_an_empty_result():
    records, _ = _page_number_fetch([_http_error(406)])
    assert records == []


def test_other_client_errors_still_propagate():
    with pytest.raises(requests.HTTPError):
        _page_number_fetch([_http_error(401)])


def test_fetch_one_returns_none_when_the_record_does_not_exist():
    with patch("requests.get", side_effect=[_http_error(406)]):
        assert APIFetcher("http://fake", "token").fetch_one("/buscar/boleto/1") is None


def test_a_non_json_answer_is_retried():
    """A maintenance page served with 200 is transient; parsing outside the retry
    turned it into a failed status on the first attempt."""
    bad = MagicMock()
    bad.raise_for_status.return_value = None
    bad.json.side_effect = requests.exceptions.JSONDecodeError("Expecting value", "", 0)
    good = _ok({"voluntarios": [{"codigo_voluntario": 1}]})

    with patch("requests.get", side_effect=[bad, good]), patch("infra.retry.time.sleep"):
        fetcher = APIFetcher("http://fake", "token")
        records = fetcher.fetch_by_page("/listar/voluntario/ativo", {}, "pagina", "voluntarios")

    assert records == [{"codigo_voluntario": 1}]


def test_deduplicate_by_key_refuses_records_without_the_key():
    """Keyed under None, a renamed field would collapse the batch into one row."""
    with pytest.raises(ValueError, match="without 'id'"):
        deduplicate_by_key([{"id": 1}, {"other": 2}, {"other": 3}], "id")
