import re
from pathlib import Path

import pytest

from infra.raw_writer import KNOWN_ENTITIES, write_raw


def test_rejects_an_unknown_entity():
    """ The entity name is interpolated into the SQL, so the allowlist is a boundary."""
    with pytest.raises(ValueError, match="Unknown raw entity"):
        write_raw("regionals; drop table dim_vehicles", "/x", [{"a": 1}])


def test_rejects_empty_batch():
    """Zero records means a failed extraction, and must not land as a valid batch."""
    with pytest.raises(ValueError, match="empty batch"):
        write_raw("regionals", "/listar/regional/ativo", [])


def test_allowlist_matches_the_ddl():
    """The allowlist and the DDL are two lists of the same thing.
    
    Nothing else checks that they agree: an entity missing here is rejected at
    write time and swallowed by write_raw_shadow, so the table simply stays
    empty while the pipeline keeps reporting success.
    """
    ddl = Path("sql/ddl/010_raw_schema.sql").read_text(encoding="utf-8")
    declared = set(re.findall(r"CREATE TABLE IF NOT EXISTS raw\.(\w+)", ddl))

    assert declared == set(KNOWN_ENTITIES)