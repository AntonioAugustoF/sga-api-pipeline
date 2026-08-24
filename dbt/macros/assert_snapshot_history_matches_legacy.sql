{% macro assert_snapshot_history_matches_legacy(snapshot_name, legacy_table, natural_key) %}
    {#-
      Compares the full version timeline of a snapshot against the SCD2 table
      the Python path maintains: every (natural key, valid from, valid to)
      interval must exist on both sides.

      Compared at date granularity on purpose. load/scd2.py stamps a
      reference_date, while dbt stamps the moment the snapshot ran, so the same
      version legitimately reads 2026-08-25 on one side and
      2026-08-25 03:15:22 on the other. The day is the business fact; the clock
      time is an implementation detail.
    -#}

    with snapshot_side as (

        select
            {{ natural_key }},
            dbt_valid_from::date as valido_de,
            dbt_valid_to::date   as valido_ate
        from {{ ref(snapshot_name) }}

    ), legacy_side as (

        select
            {{ natural_key }},
            valido_de,
            valido_ate
        from {{ source('warehouse', legacy_table) }}

    )

    select 'only_in_snapshot' as lado, * from (select * from snapshot_side except select * from legacy_side) s
    union all
    select 'only_in_legacy', * from (select * from legacy_side except select * from snapshot_side) l

{% endmacro %}
