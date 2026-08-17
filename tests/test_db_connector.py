from unittest.mock import patch

from infra.db_connector import get_db_engine

CREDENTIALS = {
    "DB_USER": "pipeline_user",
    "DB_PASSWORD": "s3nh4-c0m/barra@e-arroba",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_NAME": "sga_dw",
}


def _build_engine():
    """Builds the engine with fake credentials, bypassing the module-level cache."""
    get_db_engine.cache_clear()
    with patch.multiple("infra.db_connector.config", **CREDENTIALS):
        return get_db_engine()


def test_password_is_never_rendered_in_the_url():
    """A URL aparece em mensagens de erro de conexão; a senha não pode ir nela.

    URL.create mascara a senha no str/repr, ao contrário da f-string anterior.
    """
    engine = _build_engine()

    assert CREDENTIALS["DB_PASSWORD"] not in str(engine.url)
    assert CREDENTIALS["DB_PASSWORD"] not in repr(engine.url)
    assert CREDENTIALS["DB_PASSWORD"] not in str(engine)
    assert "***" in str(engine.url)


def test_password_survives_intact_for_authentication():
    """Mascarar é só na renderização — a senha real precisa chegar ao driver."""
    engine = _build_engine()

    assert engine.url.password == CREDENTIALS["DB_PASSWORD"]


def test_url_components_are_escaped_not_just_the_password():
    """A f-string antiga escapava só a senha; usuario/host/base entravam crus."""
    engine = _build_engine()

    assert engine.url.username == CREDENTIALS["DB_USER"]
    assert engine.url.host == CREDENTIALS["DB_HOST"]
    assert engine.url.database == CREDENTIALS["DB_NAME"]
    assert engine.url.port == 5432


def test_engine_is_cached_per_process():
    """Um único pool por processo, em vez de um por loader."""
    engine = _build_engine()
    with patch.multiple("infra.db_connector.config", **CREDENTIALS):
        assert get_db_engine() is engine

    get_db_engine.cache_clear()
