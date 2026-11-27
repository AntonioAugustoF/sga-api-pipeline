-- One row per invoice: fact_invoices_base plus the two aging measures.
--
-- The aging measures live in a view because they are a function of the day
-- the fact is read. They used to be persisted in the incremental model, where
-- an invoice only gets merged again while it is inside an extraction window:
-- an unpaid invoice that left the windows kept the age it had that day. On
-- 2026-11-27, 5,027 unpaid invoices sat in the wrong band, most of them in
-- '0-30' while 31 to 300 days overdue.
--
-- Same name and same columns as the table it replaces, so consumers do not
-- change. The rule is the legacy one: cleared once paid, floored at zero.
-- coalesce guards the null flag, which pandas counted as unpaid.

{{ config(materialized = 'view') }}

select
    f.*,

    case
        when coalesce(f.pago, '') = 'y' then null
        when f.data_vencimento is null   then null
        else {{ dias_em_atraso('f.data_vencimento', aging_as_of()) }}
    end as dias_em_atraso,

    case
        when coalesce(f.pago, '') = 'y' then null
        else {{ faixa_atraso('f.data_vencimento', aging_as_of()) }}
    end as faixa_atraso

from {{ ref('fact_invoices_base') }} f
