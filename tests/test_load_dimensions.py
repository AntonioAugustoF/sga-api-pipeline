import pytest

from load.load_dimensions import assert_no_abnormal_drop


def test_assert_no_abnormal_drop_allows_first_load():
    assert_no_abnormal_drop(current_count=100, previous_count=0, entity_name="customers")


def test_assert_no_abnormal_drop_allows_small_drop():
    assert_no_abnormal_drop(current_count=950, previous_count=1000, entity_name="customers")


def test_assert_no_abnormal_drop_allows_growth():
    assert_no_abnormal_drop(current_count=1100, previous_count=1000, entity_name="customers")


def test_assert_no_abnormal_drop_raises_on_partial_extraction():
    with pytest.raises(ValueError, match="customers"):
        assert_no_abnormal_drop(current_count=200, previous_count=1000, entity_name="customers")
