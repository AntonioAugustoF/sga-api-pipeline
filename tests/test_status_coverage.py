from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from load.load_dimensions import warn_on_status_coverage_change
from transform.transform_statuses import _to_boolean

TABLE = "dim_status"
KEY = "codigo_situacao"
DESC = "descricao_situacao"


def _engine_with(rows, has_table=True):
    """Builds an engine whose SELECT on the dimension returns the given (code, description) rows."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.all.return_value = rows
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    inspector = MagicMock()
    inspector.has_table.return_value = has_table
    return mock_engine, inspector


def _run(df, rows, has_table=True):
    engine, inspector = _engine_with(rows, has_table)
    with patch("load.load_dimensions.inspect", return_value=inspector), \
         patch("load.load_dimensions.send_status_coverage_alert") as alert:
        warn_on_status_coverage_change(engine, TABLE, KEY, DESC, df)
    return alert


def _df(pairs):
    return pd.DataFrame(pairs, columns=[KEY, DESC])


def test_no_alert_when_status_list_is_unchanged():
    df = _df([("1", "ativo"), ("2", "inativo")])
    alert = _run(df, rows=[("1", "ativo"), ("2", "inativo")])
    alert.assert_not_called()


def test_alerts_on_newly_granted_status():
    df = _df([("1", "ativo"), ("19", "reativação 30+")])
    alert = _run(df, rows=[("1", "ativo")])

    _, added, removed = alert.call_args[0]
    assert added == {"19": "reativação 30+"}
    assert removed == {}


def test_alerts_when_status_disappears_from_source():
    """The failure mode that left vehicles unextracted: a status silently stops being returned."""
    df = _df([("1", "ativo")])
    alert = _run(df, rows=[("1", "ativo"), ("19", "reativação 30+")])

    _, added, removed = alert.call_args[0]
    assert added == {}
    assert removed == {"19": "reativação 30+"}


def test_skips_check_on_first_load():
    df = _df([("1", "ativo")])
    alert = _run(df, rows=[], has_table=False)
    alert.assert_not_called()


def test_never_raises_when_the_check_itself_fails():
    """A broken coverage check must not fail the dimension load."""
    engine = MagicMock()
    engine.connect.side_effect = RuntimeError("connection lost")
    inspector = MagicMock()
    inspector.has_table.return_value = True

    with patch("load.load_dimensions.inspect", return_value=inspector):
        warn_on_status_coverage_change(engine, TABLE, KEY, DESC, _df([("1", "ativo")]))


def test_compares_codes_as_strings_regardless_of_source_type():
    """The DW stores codes as text; the API may hand back ints."""
    df = pd.DataFrame({KEY: [1, 2], DESC: ["ativo", "inativo"]})
    alert = _run(df, rows=[("1", "ativo"), ("2", "inativo")])
    alert.assert_not_called()


@pytest.mark.parametrize("raw, expected", [
    ("Y", True), ("N", False),
    ("SIM", True), ("NÃO", False),
    ("sim", True), ("y", True),
])
def test_to_boolean_maps_source_flags(raw, expected):
    result = _to_boolean(pd.Series([raw]), {"y", "s", "sim"})
    assert bool(result.iloc[0]) is expected


def test_to_boolean_preserves_nulls():
    result = _to_boolean(pd.Series([None]), {"y", "sim"})
    assert pd.isna(result.iloc[0])
