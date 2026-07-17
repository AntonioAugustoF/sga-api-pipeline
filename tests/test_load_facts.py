from contextlib import contextmanager
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import types as sa_types

from load.load_facts import (
    _infer_pg_type,
    _infer_sa_type,
    add_audit_columns,
    resolve_point_in_time_sk,
    upsert_to_postgres,
)


# ---------------------------------------------------------------------------
# _infer_pg_type / _infer_sa_type
# ---------------------------------------------------------------------------

def test_infer_pg_type_bool():
    assert _infer_pg_type(pd.Series([True, False])) == "BOOLEAN"


def test_infer_pg_type_integer():
    assert _infer_pg_type(pd.Series([1, 2, 3])) == "BIGINT"


def test_infer_pg_type_nullable_integer():
    # Int64 (nullable) is what resolve_point_in_time_sk produces; must stay integer.
    assert _infer_pg_type(pd.Series([1, None], dtype="Int64")) == "BIGINT"


def test_infer_pg_type_float():
    assert _infer_pg_type(pd.Series([1.5, 2.5])) == "DOUBLE PRECISION"


def test_infer_pg_type_datetime64():
    assert _infer_pg_type(pd.to_datetime(pd.Series(["2026-01-01"]))) == "TIMESTAMP"


def test_infer_pg_type_object_of_dates():
    # cast_date_columns yields object-dtype Series of Python date objects.
    assert _infer_pg_type(pd.Series([date(2026, 1, 1), date(2026, 2, 1)])) == "DATE"


def test_infer_pg_type_object_of_datetimes():
    assert _infer_pg_type(pd.Series([datetime(2026, 1, 1, 12, 0)])) == "TIMESTAMP"


def test_infer_pg_type_text_fallback():
    assert _infer_pg_type(pd.Series(["a", "b"])) == "TEXT"


def test_infer_sa_type_stays_in_sync_with_pg_type():
    # The two inferrers drifting apart is exactly what caused sk_customer to
    # land as DOUBLE PRECISION; assert they agree on the key cases.
    cases = {
        "BOOLEAN": (pd.Series([True]), sa_types.Boolean),
        "BIGINT": (pd.Series([1], dtype="Int64"), sa_types.BigInteger),
        "DOUBLE PRECISION": (pd.Series([1.5]), sa_types.Float),
        "DATE": (pd.Series([date(2026, 1, 1)]), sa_types.Date),
        "TEXT": (pd.Series(["x"]), sa_types.Text),
    }
    for pg, (series, sa_cls) in cases.items():
        assert _infer_pg_type(series) == pg
        assert isinstance(_infer_sa_type(series), sa_cls)


# ---------------------------------------------------------------------------
# add_audit_columns
# ---------------------------------------------------------------------------

def test_add_audit_columns_adds_all_three():
    df = pd.DataFrame({"codigo_boleto": ["B1"]})
    result = add_audit_columns(df, reference_date=date(2026, 7, 17))
    assert {"criado_em", "atualizado_em", "data_referencia"} <= set(result.columns)
    assert result["data_referencia"].iloc[0] == date(2026, 7, 17)


def test_add_audit_columns_can_skip_data_referencia():
    df = pd.DataFrame({"codigo_boleto": ["B1"]})
    result = add_audit_columns(df, reference_date=date(2026, 7, 17), include_data_referencia=False)
    assert "data_referencia" not in result.columns
    assert {"criado_em", "atualizado_em"} <= set(result.columns)


def test_add_audit_columns_does_not_mutate_original():
    df = pd.DataFrame({"codigo_boleto": ["B1"]})
    add_audit_columns(df, reference_date=date(2026, 7, 17))
    assert "criado_em" not in df.columns


# ---------------------------------------------------------------------------
# resolve_point_in_time_sk
# ---------------------------------------------------------------------------

@pytest.fixture
def dim_customers_frame():
    # A1 has two SCD2 versions; A2 is absent from the dimension.
    return pd.DataFrame({
        "codigo_associado": ["A1", "A1"],
        "sk_customer": [1, 2],
        "valido_de": ["1900-01-01", "2026-06-01"],
        "valido_ate": ["2026-06-01", None],
    })


def _resolve(df, dim_frame, has_table=True):
    engine = MagicMock()
    with patch("load.load_facts.inspect") as mock_inspect, \
         patch("load.load_facts.pd.read_sql", return_value=dim_frame):
        mock_inspect.return_value.has_table.return_value = has_table
        return resolve_point_in_time_sk(
            engine, df,
            dim_table="dim_customers",
            dim_natural_key="codigo_associado",
            dim_sk_col="sk_customer",
            fact_natural_key="codigo_associado",
            fact_date_col="data_emissao",
        )


def test_resolve_sk_missing_dim_table_returns_all_null():
    df = pd.DataFrame({"codigo_associado": ["A1"], "data_emissao": [date(2025, 1, 1)]})
    result = _resolve(df, pd.DataFrame(), has_table=False)
    assert result["sk_customer"].isna().all()


def test_resolve_sk_point_in_time_picks_effective_version(dim_customers_frame):
    df = pd.DataFrame({
        "codigo_associado": ["A1", "A1"],
        "data_emissao": [date(2025, 1, 1), date(2026, 7, 1)],
    })
    result = _resolve(df, dim_customers_frame)
    # 2025 falls in the first version (sk=1); 2026-07 in the current one (sk=2).
    assert result["sk_customer"].tolist() == [1, 2]


def test_resolve_sk_unmatched_key_is_na(dim_customers_frame):
    df = pd.DataFrame({
        "codigo_associado": ["A1", "A2"],
        "data_emissao": [date(2026, 7, 1), date(2025, 1, 1)],
    })
    result = _resolve(df, dim_customers_frame)
    assert result["sk_customer"].iloc[0] == 2
    assert pd.isna(result["sk_customer"].iloc[1])


def test_resolve_sk_result_is_nullable_integer(dim_customers_frame):
    # Regression: NaN from unmatched rows must not upcast the column to float,
    # which silently created fact_invoices.sk_customer as DOUBLE PRECISION.
    df = pd.DataFrame({
        "codigo_associado": ["A2"],
        "data_emissao": [date(2025, 1, 1)],
    })
    result = _resolve(df, dim_customers_frame)
    assert str(result["sk_customer"].dtype) == "Int64"


# ---------------------------------------------------------------------------
# upsert_to_postgres — composite key & immutable columns
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    mock_conn = MagicMock()
    mock_engine = MagicMock()

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.begin = fake_begin
    return mock_engine, mock_conn


def _executed_sql(mock_conn):
    out = []
    for call in mock_conn.execute.call_args_list:
        arg = call[0][0]
        out.append(arg.text if hasattr(arg, "text") else str(arg))
    return out


def test_upsert_composite_key_excludes_immutable_from_update(mock_db):
    mock_engine, mock_conn = mock_db
    df = pd.DataFrame({
        "codigo_boleto": ["B1"],
        "codigo_veiculo": ["V1"],
        "valor_rateado": [100.0],
        "criado_em": [datetime(2026, 7, 17)],
    })

    with patch("load.load_facts.get_db_engine", return_value=mock_engine), \
         patch("load.load_facts.inspect") as mock_inspect, \
         patch("load.load_facts.sync_table_schema"), \
         patch.object(pd.DataFrame, "to_sql"):
        mock_inspect.return_value.has_table.return_value = True
        upsert_to_postgres(
            df, "bridge_invoices_vehicles",
            pk_column=["codigo_boleto", "codigo_veiculo"],
            immutable_columns=["criado_em"],
        )

    inserts = [s for s in _executed_sql(mock_conn) if "INSERT INTO" in s]
    assert inserts, "expected an INSERT ... ON CONFLICT statement"
    sql = inserts[0]
    # Composite conflict target present.
    assert 'ON CONFLICT ("codigo_boleto", "codigo_veiculo")' in sql
    # Mutable column is refreshed...
    assert '"valor_rateado" = EXCLUDED."valor_rateado"' in sql
    # ...but PK and immutable columns are never overwritten.
    assert '"criado_em" = EXCLUDED' not in sql
    assert '"codigo_boleto" = EXCLUDED' not in sql
