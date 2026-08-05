from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from load.load_dimensions import assert_no_abnormal_drop, run_dimensions_load


def test_assert_no_abnormal_drop_allows_first_load():
    assert_no_abnormal_drop(current_count=100, previous_count=0, entity_name="customers")


def test_assert_no_abnormal_drop_allows_small_drop():
    assert_no_abnormal_drop(current_count=950, previous_count=1000, entity_name="customers")


def test_assert_no_abnormal_drop_allows_growth():
    assert_no_abnormal_drop(current_count=1100, previous_count=1000, entity_name="customers")


def test_assert_no_abnormal_drop_raises_on_partial_extraction():
    with pytest.raises(ValueError, match="customers"):
        assert_no_abnormal_drop(current_count=200, previous_count=1000, entity_name="customers")


def _patched_load(fail_on: str | None):
    """Runs run_dimensions_load with every I/O boundary stubbed out.
    
    `fail_on` names the entity whose processed file is missing, which is how a
    real failure reaches the expect block inside the loop.
    """
    df = pd.DataFrame({"codigo_cooperativa": ["1"], "descricao_situacao": ["Ativo"]})

    def resolve_file(entity, *args, **kwargs):
        if entity == fail_on:
            raise FileNotFoundError(f"No processed Parquet file found for entity: {entity}")
        return f"{entity}.parquet"

    return patch.multiple(
        "load.load_dimensions",
        get_db_engine=MagicMock(return_value=MagicMock()),
        get_latest_processed_file=MagicMock(side_effect=resolve_file),
        get_current_row_count=MagicMock(return_value=0),
        warn_on_status_coverage_change=MagicMock(),
        add_audit_columns=MagicMock(return_value=df),
        upsert_to_postgres=MagicMock(),
        upsert_scd2_dimension=MagicMock(),
    ), df


def test_run_dimensions_load_raises_when_entity_fails():
    """Regression: a failed entity was only a warning, so the flow reported success.
    
    Facts were then loaded against dimensions that had not been refreshed — which
    is how vehicles ended up with no current version and no attribution for days.
    """
    patches, df = _patched_load(fail_on="vehicles")

    with patches, patch("pandas.read_parquet", return_value=df), pytest.raises(RuntimeError, match="vehicles"):
        run_dimensions_load()


def test_run_dimensions_load_is_silent_when_every_entity_loads():
    patches, df = _patched_load(fail_on=None)

    with patches, patch("pandas.read_parquet",return_value=df):
        run_dimensions_load()