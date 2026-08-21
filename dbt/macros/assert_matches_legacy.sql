{% macro assert_matches_legacy(model_name, legacy_table, columns) %}
    {#-
      Body shared by every phase reconciliation test. EXCEPT is used rather than
      a join because it treats NULL as equal to NULL, which a join predicate
      does not. Both directions are checked: a row present only in the legacy
      table is as much a failure as an extra row on the dbt side.
    -#}

    with dbt_side as (

        select {{ columns | join(', ') }}
        from {{ ref(model_name) }}

    ), legacy_side as (

        select {{ columns | join(', ') }}
        from {{ source('warehouse', legacy_table) }}

    )

    select 'only_in_dbt' as lado, * from (select * from dbt_side except select * from legacy_side) d
    union all
    select 'only_in_legacy', * from (select * from legacy_side except select * from dbt_side) l

{% endmacro %}
