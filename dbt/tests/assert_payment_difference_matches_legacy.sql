-- diferenca_pagamento is computed in numeric here and was computed in binary
-- floating point in the legacy table, so the two agree only up to float noise.
-- The tolerance is the same 0.005 used by assert_rateio_reconstructs_invoice_value:
-- half a cent, well above the observed 1e-12 and well below anything that would
-- change a business decision.

with dbt_side as (

    select codigo_boleto, diferenca_pagamento
    from {{ ref('fact_invoices') }}

), legacy_side as (

    select codigo_boleto, diferenca_pagamento
    from {{ source('warehouse', 'fact_invoices') }}

)

select
    d.codigo_boleto,
    d.diferenca_pagamento as valor_dbt,
    l.diferenca_pagamento as valor_legado
from dbt_side d
join legacy_side l using (codigo_boleto)
where abs(d.diferenca_pagamento::double precision - l.diferenca_pagamento) > 0.005
   or (d.diferenca_pagamento is null) <> (l.diferenca_pagamento is null)
