-- The invariant the bridge exists to satisfy: the shares of an invoice must add
-- back up to the invoice. The legacy version of this test tolerates 0.005
-- because double precision cannot divide cleanly; this one runs against the
-- numeric model, where the only remaining error is the repeating decimal of a
-- three-way or seven-way split.
--
-- Worth keeping separate from the legacy test rather than replacing it: while
-- both paths run, a divergence should say which one drifted.

with invoices as (

    select codigo_boleto, valor_boleto from {{ ref('fact_invoices') }}

), bridge as (

    select codigo_boleto, valor_rateado from {{ ref('bridge_invoices_vehicles') }}

)

select
    i.codigo_boleto,
    i.valor_boleto,
    sum(b.valor_rateado) as soma_rateada
from invoices i
join bridge b using (codigo_boleto)
group by i.codigo_boleto, i.valor_boleto
having abs(sum(b.valor_rateado) - i.valor_boleto) > 0.005
