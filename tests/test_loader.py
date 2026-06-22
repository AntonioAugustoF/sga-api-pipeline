import json
import os
from datetime import datetime

import pytest

from infra.loader import load_raw_to_dataframe, load_status_lookup


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw_path = tmp_path / "data" / "raw"
    raw_path.mkdir(parents=True)
    return raw_path


def test_load_raw_to_dataframe_reads_todays_file(raw_dir):
    today = datetime.now().strftime("%Y-%m-%d")
    data = [{"codigo_associado": 1, "nome": "Ana"}]
    (raw_dir / f"customers_{today}.json").write_text(
        json.dumps(data), encoding="utf-8"
    )

    df = load_raw_to_dataframe("customers")

    assert len(df) == 1
    assert df.iloc[0]["nome"] == "Ana"


def test_load_raw_to_dataframe_missing_file_raises(raw_dir):
    with pytest.raises(FileNotFoundError):
        load_raw_to_dataframe("customers")


def test_load_status_lookup_reads_todays_file(raw_dir):
    today = datetime.now().strftime("%Y-%m-%d")
    lookup = {"1": "ativo", "2": "inativo"}
    (raw_dir / f"customers_status_lookup_{today}.json").write_text(
        json.dumps(lookup), encoding="utf-8"
    )

    result = load_status_lookup("customers")

    assert result == lookup


def test_load_status_lookup_missing_file_raises(raw_dir):
    with pytest.raises(FileNotFoundError):
        load_status_lookup("customers")
