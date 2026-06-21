import pandas as pd
import pytest

from infra.transformations import (
    rename_columns,
    remove_duplicates,
    remove_empty_rows,
    cast_string_columns,
    cast_date_columns,
    cast_numeric_columns,
)


def test_rename_columns_lowercases_and_strips():
    df = pd.DataFrame(columns=[" Nome ", "CPF", " Email"])
    result = rename_columns(df)
    assert list(result.columns) == ["nome", "cpf", "email"]


def test_remove_duplicates_keeps_first_occurrence():
    df = pd.DataFrame({"id": [1, 1, 2], "value": ["a", "b", "c"]})
    result = remove_duplicates(df, subset=["id"])
    assert result["value"].tolist() == ["a", "c"]


def test_remove_empty_rows_drops_fully_null_rows_only():
    df = pd.DataFrame({"a": [1, None, None], "b": [2, None, 3]})
    result = remove_empty_rows(df)
    assert len(result) == 2


def test_cast_string_columns_strips_and_lowercases():
    df = pd.DataFrame({"nome": ["  Ana  ", "BETO"]})
    result = cast_string_columns(df, ["nome"])
    assert result["nome"].tolist() == ["ana", "beto"]


def test_cast_string_columns_preserves_nulls():
    df = pd.DataFrame({"nome": ["Ana", None]})
    result = cast_string_columns(df, ["nome"])
    assert result["nome"].iloc[1] is None


def test_cast_date_columns_parses_valid_dates():
    df = pd.DataFrame({"data": ["2024-01-15", "2024-03-20"]})
    result = cast_date_columns(df, ["data"])
    assert result["data"].iloc[0].isoformat() == "2024-01-15"


@pytest.mark.filterwarnings("ignore:Could not infer format")
def test_cast_date_columns_coerces_invalid_to_none():
    df = pd.DataFrame({"data": ["not-a-date", "2024-03-20"]})
    result = cast_date_columns(df, ["data"])
    assert result["data"].iloc[0] is None


def test_cast_numeric_columns_converts_valid_values():
    df = pd.DataFrame({"valor": ["10.5", "20"]})
    result = cast_numeric_columns(df, ["valor"])
    assert result["valor"].tolist() == [10.5, 20.0]


def test_cast_numeric_columns_coerces_invalid_to_nan():
    df = pd.DataFrame({"valor": ["abc", "20"]})
    result = cast_numeric_columns(df, ["valor"])
    assert pd.isna(result["valor"].iloc[0])
    assert result["valor"].iloc[1] == 20.0
