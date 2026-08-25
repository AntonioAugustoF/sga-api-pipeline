-- Phase 4b: sk_customer changed meaning in phase 3c, from a SERIAL integer to
-- the snapshot's hash, so the values cannot be compared directly. What has to
-- hold is that both sides point at the same customer version.
--
-- Each side resolves its own key back to (codigo_associado, valido_de) and the
-- two sets must be identical. That is a stronger claim than comparing the keys
-- would be: it validates the point-in-time rule itself, not just the label. A
-- silent off-by-one-version here would credit revenue to the wrong volunteer
-- while every column-by-column test stayed green.
--
-- Relations are imported as CTEs rather than aliased inline, for the reason
-- recorded in the CI workflow: under --empty dbt wraps them in a subquery that
-- already carries an alias.

with dbt_facts as (

    select codigo_boleto, sk_customer from {{ ref('fact_invoices') }}

), dbt_dim as (

    select sk_customer, codigo_associado, valido_de from {{ ref('dim_customers') }}

), legacy_facts as (

    select codigo_boleto, sk_customer from {{ source('warehouse', 'fact_invoices') }}

), legacy_dim as (

    select sk_customer, codigo_associado, valido_de from {{ source('warehouse', 'dim_customers') }}

), dbt_side as (

    select f.codigo_boleto, d.codigo_associado, d.valido_de
    from dbt_facts f
    left join dbt_dim d using (sk_customer)

), legacy_side as (

    select f.codigo_boleto, d.codigo_associado, d.valido_de
    from legacy_facts f
    left join legacy_dim d using (sk_customer)

)

select 'only_in_dbt' as lado, * from (select * from dbt_side except select * from legacy_side) d
union all
select 'only_in_legacy', * from (select * from legacy_side except select * from dbt_side) l
