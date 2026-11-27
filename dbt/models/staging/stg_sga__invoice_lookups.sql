-- One row per invoice re-read through /buscar/boleto in THIS run: the open
-- invoices that left the open status outside every extraction window (see
-- extract/extract_invoice_lookups.py).
--
-- Only the fields fact_invoices_base overrides are exposed. The lookup payload
-- is a different shape from the listing — no `pago`, no `veiculo`, other names
-- for the regional and bank columns, and a forma de pagamento that disagrees
-- with the listing for the same invoice — so it corrects state, it does not
-- replace rows.
--
-- `pago` is derived: the lookup does not carry it. Across the 323,092 invoices
-- in the fact on 2026-11-27 the listing's flag was 'y' exactly when the status
-- was 1 (baixado) or 4, without exception.
--
-- A batch older than the latest invoice extraction is ignored. Without that
-- filter a night with nothing to reconcile would re-apply the previous lookup
-- batch on top of fresher data from the listing.

with latest_batch as (

    select payload, _extracted_at
    from {{ source('sga', 'invoice_lookups') }}
    where _extracted_at = (select max(_extracted_at) from {{ source('sga', 'invoice_lookups') }})
      and _extracted_at > (select max(_extracted_at) from {{ source('sga', 'invoices') }})

)

select
    {{ clean_json_string('codigo_boleto') }}               as codigo_boleto,
    {{ clean_json_string('codigo_situacao_boleto') }}      as codigo_situacao_boleto,
    {{ clean_json_string('descricao_situacao_boleto') }}   as descricao_situacao_boleto,
    case
        when {{ clean_json_string('codigo_situacao_boleto') }} in ('1', '4') then 'y'
        else 'n'
    end                                                     as pago,
    {{ try_json_cast('data_vencimento', 'date') }}         as data_vencimento,
    {{ try_json_cast('valor_boleto', 'numeric') }}         as valor_boleto,
    {{ try_json_cast('data_pagamento', 'date') }}          as data_pagamento,
    {{ try_json_cast('valor_pagamento', 'numeric') }}      as valor_pagamento,
    {{ try_json_cast('data_credito_banco', 'date') }}      as data_credito_banco,
    {{ clean_json_string('descricao_tipo_baixa_boleto') }} as descricao_tipo_baixa_boleto,
    {{ try_json_cast('parcela_paga', 'bigint') }}          as parcela_paga,
    -- The listing stamps the status it was queried by; for a lookup that is
    -- the invoice's own status.
    {{ clean_json_string('codigo_situacao_boleto') }}      as codigo_situacao,
    _extracted_at
from latest_batch
