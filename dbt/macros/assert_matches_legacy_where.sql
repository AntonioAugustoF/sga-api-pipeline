{% macro assert_matches_legacy_where(model_name, legacy_table, legacy_filter, columns) %}
    {#-
      Variant of assert_matches_legacy for SCD2 legacy tables, where only a
      subset of rows describes the present. legacy_filter is a boolean
      expression applied to the legacy side only.
    -#}

    with dbt_side as (

        select {{ columns | join(', ') }}
        from {{ ref(model_name) }}

    ), legacy_side as (

        select {{ columns | join(', ') }}
        from {{ source('warehouse', legacy_table) }}
        where {{ legacy_filter }}

    )

    select 'only_in_dbt' as lado, * from (select * from dbt_side except select * from legacy_side) d
    union all
    select 'only_in_legacy', * from (select * from legacy_side except select * from dbt_side) l

{% endmacro %}
