from infra.freshness import find_stale


def test_no_stale_tables_when_everything_is_recent():
    assert find_stale({"dim_vehicles": 3.2, "fact_invoices": 3.5}, max_age_hours=26) == {}


def test_flags_a_table_past_the_limit():
    stale = find_stale({"dim_vehicles": 3.2, "fact_invoices": 51.0}, max_age_hours=26)
    assert stale == {"fact_invoices": 51.0}


def test_a_table_never_written_counts_as_stale():
    """A missing MAX() means the table was never loaded, which is worse than being late."""
    assert find_stale({"dim_vehicles": None}, max_age_hours=26) == {"dim_vehicles": None}


def test_a_late_but_acceptable_run_does_not_alert():
    """The daily run starts at 03:00; 26h absorbs one that merely started late."""
    assert find_stale({"dim_vehicles": 25.5}, max_age_hours=26) == {}