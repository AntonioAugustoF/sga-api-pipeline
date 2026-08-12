-- The invoice proration must sum back to the amount frozen in the snapshot.
-- In addition to validating the split, this guards against fan-out: if the bridge has
-- more rows for the invoice than qtd_veiculos_boleto specifies, the sum will exceed the total.
select dt_referencia, codigo_boleto
from {{ ref('int_delinquency_by_vehicle') }}
where valor_rateado is not null
group by dt_referencia, codigo_boleto, valor_boleto
having abs(sum(valor_rateado) - valor_boleto) > 0.005
