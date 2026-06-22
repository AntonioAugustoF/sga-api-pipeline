from unittest.mock import MagicMock, patch

from infra.api_fetcher import APIFetcher, deduplicate_by_key


def _mock_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_fetch_by_page_stops_when_page_smaller_than_page_size():
    responses = [
        _mock_response({"voluntarios": [{"codigo_voluntario": 1}, {"codigo_voluntario": 2}]}),
        _mock_response({"voluntarios": [{"codigo_voluntario": 3}]}),
    ]

    with patch("requests.get", side_effect=responses) as mock_get:
        fetcher = APIFetcher("http://fake", "token", page_size=2)
        records = fetcher.fetch_by_page(
            "/listar/voluntario/ativo", {"situacao": "ativo"}, "pagina", "voluntarios"
        )

    assert [r["codigo_voluntario"] for r in records] == [1, 2, 3]
    assert mock_get.call_count == 2


def test_fetch_by_page_stops_on_empty_page():
    responses = [_mock_response({"voluntarios": []})]

    with patch("requests.get", side_effect=responses):
        fetcher = APIFetcher("http://fake", "token", page_size=5000)
        records = fetcher.fetch_by_page(
            "/listar/voluntario/ativo", {"situacao": "ativo"}, "pagina", "voluntarios"
        )

    assert records == []


def test_fetch_by_page_handles_bare_list_response():
    responses = [_mock_response([{"codigo_voluntario": 1}])]

    with patch("requests.get", side_effect=responses):
        fetcher = APIFetcher("http://fake", "token", page_size=5000)
        records = fetcher.fetch_by_page(
            "/listar/voluntario/ativo", {"situacao": "ativo"}, "pagina", "voluntarios"
        )

    assert records == [{"codigo_voluntario": 1}]


def test_fetch_by_offset_stops_when_total_reached():
    responses = [
        _mock_response({"total_associados": 3, "associados": [{"codigo_associado": 1}, {"codigo_associado": 2}]}),
        _mock_response({"total_associados": 3, "associados": [{"codigo_associado": 3}]}),
    ]

    with patch("requests.post", side_effect=responses) as mock_post:
        fetcher = APIFetcher("http://fake", "token", page_size=2)
        records = fetcher.fetch_by_offset(
            "/listar/associado",
            {"codigo_situacao": "1"},
            "inicio_paginacao",
            "quantidade_por_pagina",
            "associados",
            "total_associados",
        )

    assert [r["codigo_associado"] for r in records] == [1, 2, 3]
    assert mock_post.call_count == 2


def test_fetch_by_offset_stops_on_empty_page():
    responses = [_mock_response({"total_associados": 0, "associados": []})]

    with patch("requests.post", side_effect=responses):
        fetcher = APIFetcher("http://fake", "token", page_size=1000)
        records = fetcher.fetch_by_offset(
            "/listar/associado",
            {"codigo_situacao": "1"},
            "inicio_paginacao",
            "quantidade_por_pagina",
            "associados",
            "total_associados",
        )

    assert records == []


def test_deduplicate_by_key_keeps_first_occurrence():
    records = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}, {"id": 1, "v": "c"}]
    result = deduplicate_by_key(records, "id")
    assert result == [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]


def test_deduplicate_by_key_handles_empty_list():
    assert deduplicate_by_key([], "id") == []
