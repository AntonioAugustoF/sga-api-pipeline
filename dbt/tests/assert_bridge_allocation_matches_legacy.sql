-- valor_rateado is computed in numeric here and in binary floating point in the
-- legacy table. The observed maximum difference is 4.8e-12; the tolerance is
-- half a cent, the same one used by assert_rateio_reconstructs_invoice_value.

with dbt_side as (

    select codigo_boleto, codigo_veiculo, valor_rateado
    from {{ ref('bridge_invoices_vehicles') }}

), legacy_side as (

    select codigo_boleto, codigo_veiculo, valor_rateado
    from {{ source('warehouse', 'bridge_invoices_vehicles') }}

)

select
    d.codigo_boleto,
    d.codigo_veiculo,
    d.valor_rateado as valor_dbt,
    l.valor_rateado as valor_legado
from dbt_side d
join legacy_side l using (codigo_boleto, codigo_veiculo)
where abs(d.valor_rateado::double precision - l.valor_rateado) > 0.005
   or (d.valor_rateado is null) <> (l.valor_rateado is null)
