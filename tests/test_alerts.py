from unittest.mock import patch

import pytest

from infra.alerts import MAX_REASON_LENGTH, _mention_prefix, _redact_pii

# ---------------------------------------------------------------------------
# _redact_pii
# ---------------------------------------------------------------------------

# Mensagem real de unique-violation do psycopg2: cita o valor conflitante.
PSYCOPG_UNIQUE_VIOLATION = (
    'duplicate key value violates unique constraint "dim_customers_pkey"\n'
    "DETAIL:  Key (cpf_associado)=(12345678901) already exists."
)


def test_redacts_bare_cpf_from_a_constraint_violation():
    redacted = _redact_pii(PSYCOPG_UNIQUE_VIOLATION)

    assert "12345678901" not in redacted
    assert "[CPF]" in redacted
    # O diagnóstico precisa sobreviver à redação, senão o alerta perde utilidade.
    assert "unique constraint" in redacted
    assert "cpf_associado" in redacted


@pytest.mark.parametrize(
    ("raw", "placeholder"),
    [
        ("cpf 123.456.789-01 duplicado", "[CPF]"),
        ("cnpj 12.345.678/0001-99 invalido", "[CNPJ]"),
        ("contato fulano@empresa.com.br falhou", "[EMAIL]"),
        ("telefone (11) 98765-4321 recusado", "[TELEFONE]"),
    ],
)
def test_redacts_each_pii_shape(raw, placeholder):
    redacted = _redact_pii(raw)

    assert placeholder in redacted


def test_keeps_ordinary_diagnostics_intact():
    """Contagens e nomes de tabela não são PII e devem passar sem máscara."""
    message = "Row count for 'vehicles' dropped 40% (17917 -> 10750)."

    assert _redact_pii(message) == message


def test_truncates_long_messages():
    """Acima de 2000 caracteres o Discord rejeita a requisição inteira."""
    redacted = _redact_pii("x" * 5000)

    assert len(redacted) <= MAX_REASON_LENGTH + len(" […truncado]")
    assert redacted.endswith("[…truncado]")


# ---------------------------------------------------------------------------
# _mention_prefix
# ---------------------------------------------------------------------------

def test_mentions_the_configured_user():
    with patch("infra.alerts.config.DISCORD_ALERT_USER_ID", "123456"):
        assert _mention_prefix() == "<@123456>\n"


def test_omits_the_mention_when_unset():
    """Sem id configurado o alerta ainda vai, apenas sem mention."""
    with patch("infra.alerts.config.DISCORD_ALERT_USER_ID", None):
        assert _mention_prefix() == ""
