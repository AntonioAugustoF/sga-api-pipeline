-- One row per (reference date, invoice, vehicle) of delinquency,
-- with the prorated amount already applied.
--
-- The proration is recalculated here instead of reusing bridge.valor_rateado,
-- which might look like duplication but is not: the bridge stores the proration of the CURRENT
-- invoice amount, whereas this model is point-in-time and must prorate the amount
-- frozen as of dt_referencia. For 46 invoices, the two diverge because the amount
-- changed after the snapshot date.
--
-- Known limitation: qtd_veiculos_boleto comes from the bridge and is always the current
-- count. There is no historical record of invoice composition, so a change in the number
-- of vehicles prorates the past using today's allocation logic.
--
-- The sources are imported as CTEs rather than aliased inline. Under
-- dbt build --empty a source is replaced by a subquery that already carries
-- its own alias, and a second alias right after it is invalid SQL.

with snapshot as (

    select * from {{ source('warehouse', 'fact_delinquency_snapshot') }}

), bridge as (

    select * from {{ source('warehouse', 'bridge_invoices_vehicles') }}

)

select
    f.codigo_boleto,
    f.dt_referencia,
    f.data_emissao,
    f.data_vencimento,
    f.valor_boleto,
    f.dias_em_atraso,
    f.faixa_atraso,
    f.pago,
    b.codigo_veiculo,
    b.qtd_veiculos_boleto,
    f.valor_boleto / b.qtd_veiculos_boleto as valor_rateado
from snapshot f
left join bridge b
    on b.codigo_boleto = f.codigo_boleto
