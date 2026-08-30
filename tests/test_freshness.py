from infra.freshness import MONITORED_TABLES, find_stale


def test_no_stale_tables_when_everything_is_recent():
    assert find_stale({"analytics.dim_vehicles": 3.2, "analytics.dim_customers": 3.5}, max_age_hours=26) == {}


def test_flags_a_table_past_the_limit():
    stale = find_stale(
        {"analytics.dim_vehicles": 3.2, "analytics.fact_delinquency_snapshot": 51.0},
        max_age_hours=26,
    )
    assert stale == {"analytics.fact_delinquency_snapshot": 51.0}


def test_a_table_never_written_counts_as_stale():
    """A missing MAX() means the table was never loaded, which is worse than being late."""
    assert find_stale({"analytics.dim_vehicles": None}, max_age_hours=26) == {"analytics.dim_vehicles": None}


def test_a_late_but_acceptable_run_does_not_alert():
    """The daily run starts at 03:00; 26h absorbs one that merely started late."""
    assert find_stale({"analytics.dim_vehicles": 25.5}, max_age_hours=26) == {}


def test_yesterdays_delinquency_snapshot_is_already_stale_at_the_morning_check():
    """dt_referencia is read as hours since its midnight, which is what puts it on
    the same scale as the timestamps. The 06:00 check sees today's snapshot at 6h
    and yesterday's at 30h, so a missed night cannot pass as a late one."""
    assert find_stale({"analytics.fact_delinquency_snapshot": 30.0}, max_age_hours=26)
    assert find_stale({"analytics.fact_delinquency_snapshot": 6.0}, max_age_hours=26) == {}


def test_every_monitored_table_lives_in_analytics():
    """The cutover repointed this check. A table left qualified as public, or left
    unqualified to be resolved by search_path, would watch a schema nothing writes."""
    assert all(table.startswith("analytics.") for table in MONITORED_TABLES)
