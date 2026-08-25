-- One row per invoice, with the four derived measures and the customer version
-- that was in effect on the issue date.
--
-- Incremental, not a table, and the distinction is the whole point. Extraction
-- fetches what is new, paid or rescheduled — never the full history — so the
-- raw layer holds 7,580 invoices against the 316,918 this fact has accumulated.
-- Rebuilding from raw would silently replace the warehouse with the last batch
-- and drop 98% of the revenue history while every test stayed green, because
-- each row present would be correct.
--
-- The history is seeded by sql/migrations/002_transplant_fact_invoices.sql.
-- NEVER run this model with --full-refresh against the real warehouse: it would
-- reproduce exactly the loss described above. The same hazard as
-- `dbt build --empty`, and for the same reason — the source cannot rebuild what
-- the destination has accumulated.
--
-- No is_incremental() filter is needed: stg_sga__invoices already narrows to the
-- most recent extraction batch, so every run merges only what was just landed.
--
-- criado_em records when a row first appeared and must survive later merges,
-- matching immutable_columns in load/load_facts.py, so it is excluded from the
-- merge update. on_schema_change stops the run when a column is added to the
-- model but missing from the table, rather than ignoring it silently.
{{
    config(
        materialized = 'incremental',
        unique_key = 'codigo_boleto',
        incremental_strategy = 'merge',
        merge_exclude_columns = ['criado_em'],
        on_schema_change = 'fail',
    )
}}


with invoices as (

    select * from {{ ref('stg_sga__invoices') }}

), customer_versions as (

    select codigo_associado, sk_customer, valido_de, valido_ate
    from {{ ref('dim_customers') }}

)

select
    i.codigo_associado,
    i.nome_associado,
    i.cpf_associado,
    i.codigo_situacao_associado,
    i.descricao_situacao_associado,
    i.codigo_regional_associado,
    i.nome_regional_associado,
    i.codigo_boleto,
    i.nosso_numero,
    i.codigo_situacao_boleto,
    i.descricao_situacao_boleto,
    i.pago,
    i.codigo_regional,
    i.nome_regional_boleto,
    i.mes_referente,
    i.data_emissao,
    i.data_vencimento_original,
    i.data_vencimento,
    i.valor_boleto,
    i.data_pagamento,
    i.valor_pagamento,
    i.data_credito_banco,
    i.referente,
    i.codigo_mgfformapagamento,
    i.codigo_forma_pagamento,
    i.descricao_forma_pagamento,
    i.tarifa_cobranca_banco,
    i.parcela_paga,
    i.qtde_parcela,
    i.descricao_tipo_cobranca_recorrente,
    i.codigo_tipo_boleto,
    i.descricao_tipo_boleto,
    i.codigo_conta,
    i.codigo_banco,
    i.nome_banco,
    i.agencia,
    i.conta,
    i.descricao_tipo_baixa_boleto,
    i.veiculo,
    i.beneficiario,
    i.codigo_situacao,
    i.controle_carne,
    i.parcelado,

    -- calculate_days_overdue, floored at zero, and cleared once the invoice is
    -- paid. coalesce guards the null case: in pandas a null flag compares
    -- unequal to 'y' and the invoice counts as unpaid, while SQL would return
    -- null for the same comparison and drop the row out of every branch.
    case
        when coalesce(i.pago, '') = 'y' then null
        when i.data_vencimento is null   then null
        else greatest(current_date - i.data_vencimento, 0)
    end as dias_em_atraso,

    case
        when coalesce(i.pago, '') = 'y' then null
        when i.data_vencimento is null   then null
        when greatest(current_date - i.data_vencimento, 0) <= 30 then '0-30'
        when greatest(current_date - i.data_vencimento, 0) <= 60 then '31-60'
        when greatest(current_date - i.data_vencimento, 0) <= 90 then '61-90'
        else '90+'
    end as faixa_atraso,

    -- classify_payment_status. The null branch reproduces a quirk rather than a
    -- rule: when an invoice is flagged paid but carries no valor_pagamento,
    -- pandas computes NaN, finds abs(NaN) < 0.01 false and NaN < 0 false, and
    -- falls through to pago_a_maior. Faithfully reproduced so reconciliation
    -- holds; worth revisiting at cutover.
    case
        when coalesce(i.pago, '') <> 'y'                          then 'nao_pago'
        when i.valor_pagamento is null or i.valor_boleto is null  then 'pago_a_maior'
        when abs(i.valor_pagamento - i.valor_boleto) < 0.01       then 'pago_integral'
        when i.valor_pagamento - i.valor_boleto < 0               then 'pago_a_menor'
        else 'pago_a_maior'
    end as status_pagamento,

    i.valor_pagamento - i.valor_boleto as diferenca_pagamento,

    -- Point-in-time resolution: the customer version in effect on the issue
    -- date, not the current one. This is what keeps a past invoice credited to
    -- whoever was responsible at the time. Null when no version covers the
    -- date, which is why the epoch rule in dim_customers matters.
    v.sk_customer,

    {{ dbt.current_timestamp() }} as criado_em,

    -- From the data rather than the run date, which is the debt the legacy
    -- data_referencia carries.
    (i._extracted_at at time zone 'America/Sao_Paulo')::date as data_referencia

from invoices i
left join customer_versions v
    on v.codigo_associado = i.codigo_associado
   and i.data_emissao >= v.valido_de
   and (v.valido_ate is null or i.data_emissao < v.valido_ate)
