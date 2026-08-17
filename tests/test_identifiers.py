import pandas as pd
import pytest

from infra.identifiers import assert_safe_identifier, assert_safe_identifiers
from infra.transformations import rename_columns

# ---------------------------------------------------------------------------
# assert_safe_identifier
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name",
    ["codigo_boleto", "valor_pagamento", "sk_customer", "_temp", "dt_referencia", "cpf2"],
)
def test_accepts_warehouse_column_names(name):
    assert assert_safe_identifier(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "codigo boleto",          # espaço
        "Codigo_Boleto",          # maiúscula: rename_columns já normaliza
        "2_colunas",              # inicia com dígito
        "coluna-hifen",
        "coluna;drop",
        'coluna"aspas',
        "",
        "a" * 64,                 # acima do limite
    ],
)
def test_rejects_malformed_identifiers(name):
    with pytest.raises(ValueError):
        assert_safe_identifier(name)


def test_rejects_non_string():
    with pytest.raises(ValueError):
        assert_safe_identifier(None)


def test_error_message_names_the_context():
    with pytest.raises(ValueError, match="nome de coluna"):
        assert_safe_identifier("bad name", "nome de coluna")


# ---------------------------------------------------------------------------
# assert_safe_identifiers
# ---------------------------------------------------------------------------

def test_returns_list_unchanged_when_all_valid():
    names = ["codigo_boleto", "valor_boleto"]

    assert assert_safe_identifiers(names) == names


def test_reports_every_invalid_name_at_once():
    """Falhar em bloco evita diagnosticar uma coluna por execução."""
    with pytest.raises(ValueError) as exc:
        assert_safe_identifiers(["ok_col", "bad col", "outra-ruim"])

    assert "bad col" in str(exc.value)
    assert "outra-ruim" in str(exc.value)
    assert "ok_col" not in str(exc.value)


# ---------------------------------------------------------------------------
# Regressão: a cadeia de injeção completa, da chave da API ao identificador
# ---------------------------------------------------------------------------

INJECTION_PAYLOAD = 'x" TEXT; DROP TABLE fact_invoices CASCADE; --'


def test_blocks_the_ddl_injection_payload_that_reached_alter_table():
    """A chave hostil chegava interpolada em ALTER TABLE ... ADD COLUMN.

    O quoting f'"{col}"' era a única barreira, e a aspa dupla dentro do valor
    fechava o identificador antes da hora, emendando um segundo statement que o
    psycopg2 executa na mesma chamada.
    """
    df = rename_columns(pd.DataFrame([{"codigo_boleto": "1", INJECTION_PAYLOAD: "x"}]))

    with pytest.raises(ValueError):
        assert_safe_identifiers(list(df.columns))


def test_lowercasing_does_not_neutralize_the_payload():
    """rename_columns só faz lower/strip, e SQL é case-insensitive.

    Guarda contra alguém concluir que o lower() já sanitiza.
    """
    df = rename_columns(pd.DataFrame([{INJECTION_PAYLOAD: "x"}]))
    (column,) = df.columns

    assert "drop table" in column  # o payload sobreviveu, apenas minúsculo
    with pytest.raises(ValueError):
        assert_safe_identifier(column)
