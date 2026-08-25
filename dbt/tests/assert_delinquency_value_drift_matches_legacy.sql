-- The snapshot records what an invoice was worth on a given day; fact_invoices
-- records what it is worth now. When a value is revised after a snapshot was
-- taken, the two legitimately disagree — 63 invoices across 471 rows today,
-- and the number grows naturally as more invoices are revised.
--
-- Pinning the count would therefore be wrong: it would fail on ordinary
-- business activity. What must hold is that the dbt models reproduce the
-- legacy's behaviour exactly — the same rows drifting, by the same amounts.
-- Both sets are compared directly, so a genuine modelling error appears as a
-- row present on one side only, whatever the total happens to be that day.

with dbt_drift as (

    select s.codigo_boleto, s.dt_referencia,
           s.valor_boleto::double precision as valor_snapshot,
           i.valor_boleto::double precision as valor_atual
    from {{ ref('fact_delinquency_snapshot') }} s
    join {{ ref('fact_invoices') }} i on i.codigo_boleto = s.codigo_boleto
    where s.valor_boleto is distinct from i.valor_boleto

), legacy_drift as (

    select s.codigo_boleto, s.dt_referencia,
           s.valor_boleto::double precision as valor_snapshot,
           i.valor_boleto::double precision as valor_atual
    from {{ source('warehouse', 'fact_delinquency_snapshot') }} s
    join {{ source('warehouse', 'fact_invoices') }} i on i.codigo_boleto = s.codigo_boleto
    where s.valor_boleto is distinct from i.valor_boleto

)

select 'only_in_dbt' as lado, * from (select * from dbt_drift except select * from legacy_drift) d
union all
select 'only_in_legacy', * from (select * from legacy_drift except select * from dbt_drift) l
