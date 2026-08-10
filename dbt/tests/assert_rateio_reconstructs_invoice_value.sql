-- allocate_invoice_value_by_vehicle documents how SUM(valor_rateado) always
-- reconstructs valor_boleto. Since the columns are double precision, the division
-- doesn't add up, so this test measures how many invoices are affected and becomes the
-- evidence to migrate the monetary columns to NUMERIC.
select f.codigo_boleto
from {{ source('warehouse', 'fact_invoices') }} f
join {{ source('warehouse', 'bridge_invoices_vehicles') }} b
    on b.codigo_boleto = f.codigo_boleto
group by f.codigo_boleto, f.valor_boleto
having abs(sum(b.valor_rateado) - f.valor_boleto) > 0.005