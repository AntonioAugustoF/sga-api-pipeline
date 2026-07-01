from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from load.scd2 import upsert_scd2_dimension

@pytest.fixture
def dim_df():
    return pd.DataFrame({
        "codigo_associado": ["A1", "A2"],
        "nome": ["Alice", "Bob"],
        "codigo_situacao": ["1", "1"],
    })


@pytest.fixture
def mock_db():
    mock_conn = MagicMock()
    mock_conn.execute.return_value.rowcount = 0
    mock_engine = MagicMock()

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.begin = fake_begin
    return mock_engine, mock_conn


def _sqls(mock_conn):
    result = []
    for call in mock_conn.execute.call_args_list:
        arg = call[0][0]
        result.append(arg.text if hasattr(arg, "text") else str(arg))
    return result


def test_first_run_creates_surrogate_key_column(dim_df, mock_db):
    mock_engine, mock_conn = mock_db

    with patch("load.scd2.get_db_engine", return_value=mock_engine), \
        patch("load.scd2.inspect") as mock_inspect, \
        patch.object(pd.DataFrame, "to_sql"):
        mock_inspect.return_value.has_table.return_value = False

        upsert_scd2_dimension(
            df=dim_df,
            table_name ="dim_customers",
            natural_key="codigo_associado",
            monitored_columns=["codigo_situacao"],
            reference_date=date(2026, 7, 1),
            surrogate_key="sk_customer",
        )

    sqls = _sqls(mock_conn)
    sk_ddl = [s for s in sqls if "SERIAL PRIMARY KEY" in s]
    assert sk_ddl, f"EXPECTED SERIAL KEY DDL. Calls captured:\n{sqls}"
    assert '"sk_customer"' in sk_ddl[0]


def test_subsequent_run_sk_absent_from_insert(dim_df, mock_db):
    """sk_customer must not appear in INSERT columns - Postgres auto-generates it."""
    mock_engine, mock_conn = mock_db

    with patch("load.scd2.get_db_engine", return_value=mock_engine), \
        patch("load.scd2.inspect") as mock_inspect, \
        patch("load.scd2.sync_table_schema"), \
        patch.object(pd.DataFrame, "to_sql"):
        mock_inspect.return_value.has_table.return_value = True

        upsert_scd2_dimension(
            df=dim_df,
            table_name="dim_customers",
            natural_key="codigo_associado",
            monitored_columns=["codigo_situacao"],
            reference_date=date(2026, 7, 1),
            surrogate_key="sk_customer",
        )

    sqls = _sqls(mock_conn)
    inserts = [s for s in sqls if s.strip().upper().startswith("INSERT")]
    assert inserts, "Expected at least one INSERT statement"
    assert all("sk_customer" not in s for s in inserts)