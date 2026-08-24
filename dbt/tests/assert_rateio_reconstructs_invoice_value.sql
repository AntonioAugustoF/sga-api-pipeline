-- allocate_invoice_value_by_vehicle documents how SUM(valor_rateado) always
-- reconstructs valor_boleto. Since the columns are double precision, the division
-- doesn't add up, so this test measures how many invoices are affected and becomes the
-- evidence to migrate the monetary columns to NUMERIC.
--
-- The sources are imported as CTEs rather than aliased inline. Under
-- dbt build --empty a source is replaced by a subquery that already carries
-- its own alias, and a second alias right after it is invalid SQL.

with invoices as (

    select * from {{ source('warehouse', 'fact_invoices') }}

), bridge as (

    select * from {{ source('warehouse', 'bridge_invoices_vehicles') }}

)

select f.codigo_boleto
from invoices f
join bridge b
    on b.codigo_boleto = f.codigo_boleto
group by f.codigo_boleto, f.valor_boleto
having abs(sum(b.valor_rateado) - f.valor_boleto) > 0.005
