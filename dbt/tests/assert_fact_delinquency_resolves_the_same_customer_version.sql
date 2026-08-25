-- Phase 4d, mirroring the equivalent test on fact_invoices. sk_customer changed
-- meaning in phase 3c, from a SERIAL integer to the snapshot's hash, so the
-- values cannot be compared directly. What has to hold is that both sides point
-- at the same customer version.
--
-- Relations are imported as CTEs rather than aliased inline: under --empty dbt
-- wraps them in a subquery that already carries an alias.

with dbt_facts as (

    select codigo_boleto, dt_referencia, sk_customer
    from {{ ref('fact_delinquency_snapshot') }}

), dbt_dim as (

    select sk_customer, codigo_associado, valido_de from {{ ref('dim_customers') }}

), legacy_facts as (

    select codigo_boleto, dt_referencia, sk_customer
    from {{ source('warehouse', 'fact_delinquency_snapshot') }}

), legacy_dim as (

    select sk_customer, codigo_associado, valido_de
    from {{ source('warehouse', 'dim_customers') }}

), dbt_side as (

    select f.codigo_boleto, f.dt_referencia, d.codigo_associado, d.valido_de
    from dbt_facts f
    left join dbt_dim d using (sk_customer)

), legacy_side as (

    select f.codigo_boleto, f.dt_referencia, d.codigo_associado, d.valido_de
    from legacy_facts f
    left join legacy_dim d using (sk_customer)

)

select 'only_in_dbt' as lado, * from (select * from dbt_side except select * from legacy_side) d
union all
select 'only_in_legacy', * from (select * from legacy_side except select * from dbt_side) l
