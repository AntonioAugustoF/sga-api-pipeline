{% macro assert_matches_legacy_where_both(model_name, legacy_table, model_filter, legacy_filter, columns) %}
    {#-
      Variant of assert_matches_legacy that filters both sides. Used when the
      dbt model is itself SCD2, so "the present" has to be selected on the dbt
      side too.
    -#}

    with dbt_side as (

        select {{ columns | join(', ') }}
        from {{ ref(model_name) }}
        where {{ model_filter }}

    ), legacy_side as (

        select {{ columns | join(', ') }}
        from {{ source('warehouse', legacy_table) }}
        where {{ legacy_filter }}

    )

    select 'only_in_dbt' as lado, * from (select * from dbt_side except select * from legacy_side) d
    union all
    select 'only_in_legacy', * from (select * from legacy_side except select * from dbt_side) l

{% endmacro %}
