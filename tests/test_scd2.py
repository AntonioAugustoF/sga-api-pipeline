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


def _run_subsequent(dim_df, mock_conn, mock_engine):
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
    return _sqls(mock_conn)


def test_changed_set_is_materialized_before_closing_versions(dim_df, mock_db):
    """Regression: the changed set is defined by comparing against the current version.

    Re-evaluating it after the UPDATE cleared vigente returned an empty set, so the
    new versions were never opened and those rows were left with no current version.
    """
    mock_engine, mock_conn = mock_db
    sqls = _run_subsequent(dim_df, mock_conn, mock_engine)

    create_idx = next(i for i, s in enumerate(sqls) if "CREATE TABLE" in s and "_changed_" in s)
    update_idx = next(i for i, s in enumerate(sqls) if s.strip().upper().startswith("UPDATE"))
    assert create_idx < update_idx, "changed set must be snapshotted before versions are closed"


def test_insert_reads_changed_set_from_snapshot_not_live_table(dim_df, mock_db):
    mock_engine, mock_conn = mock_db
    sqls = _run_subsequent(dim_df, mock_conn, mock_engine)

    insert = next(s for s in sqls if s.strip().upper().startswith("INSERT"))
    assert '_changed_dim_customers' in insert
    # A live re-computation would join the dimension filtering on vigente, which is
    # exactly what the UPDATE just invalidated.
    assert "IS DISTINCT FROM" not in insert


def test_insert_targets_keys_without_a_current_version(dim_df, mock_db):
    """Self-healing: keys present in the source but with no current version get one opened."""
    mock_engine, mock_conn = mock_db
    sqls = _run_subsequent(dim_df, mock_conn, mock_engine)

    insert = next(s for s in sqls if s.strip().upper().startswith("INSERT"))
    assert "LEFT JOIN dim_customers c" in insert
    assert "c.vigente" in insert, "the LEFT JOIN must consider only current versions"


def test_new_version_starts_where_the_previous_one_ended(dim_df, mock_db):
    """Regression: the reopened version used to start on the run date.

    A key closed weeks earlier then reopened today left the days in between
    covered by no version at all, so point-in-time lookups on those dates
    resolved to nothing.
    """
    mock_engine, mock_conn = mock_db
    sqls = _run_subsequent(dim_df, mock_conn, mock_engine)

    insert = next(s for s in sqls if s.strip().upper().startswith("INSERT"))
    assert "MAX(c.valido_ate)" in insert, "valido_de must derive from the previous version's end"
    assert "1900-01-01" in insert, "a first-ever version must reach back to EPOCH"


def test_temp_tables_are_dropped(dim_df, mock_db):
    mock_engine, mock_conn = mock_db
    sqls = _run_subsequent(dim_df, mock_conn, mock_engine)

    drops = [s for s in sqls if s.strip().upper().startswith("DROP TABLE")]
    assert any("_temp_dim_customers" in s for s in drops)
    assert any("_changed_dim_customers" in s for s in drops)