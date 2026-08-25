{% macro assert_history_matches_legacy(model_name, legacy_table, natural_key) %}
    {#-
      Compares the full version timeline of a Type 2 dimension against the one
      load/scd2.py maintains: every (natural key, valido_de, valido_ate)
      interval must exist on both sides.

      Compared at the mart, not at the snapshot, and the distinction matters.
      A snapshot stamps dbt_valid_from at the moment it first saw a key, while
      load/scd2.py reaches the first version back to 1900-01-01 so that facts
      predating discovery still resolve. The mart applies that epoch rule, so it
      is the only layer where the two mechanisms are describing the same thing.
    -#}

    with dbt_side as (

        select {{ natural_key }}, valido_de, valido_ate
        from {{ ref(model_name) }}

    ), legacy_side as (

        select {{ natural_key }}, valido_de, valido_ate
        from {{ source('warehouse', legacy_table) }}

    )

    select 'only_in_dbt' as lado, * from (select * from dbt_side except select * from legacy_side) d
    union all
    select 'only_in_legacy', * from (select * from legacy_side except select * from dbt_side) l

{% endmacro %}
