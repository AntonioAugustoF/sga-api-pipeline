-- One row per (invoice, reference date): a daily photograph of what was open.
-- Unlike fact_invoices, a row here is never revised — it records what was true
-- on dt_referencia, so a value that changes tomorrow leaves today's row alone.
--
-- Incremental, seeded by
-- sql/migrations/004_transplant_fact_delinquency_snapshot.sql. The legacy table
-- holds 38 daily snapshots going back to 2026-07-01; raw.delinquency only
-- starts on 2026-08-18, so those earlier days cannot be rebuilt from source.
--
-- NEVER run with --full-refresh against the real warehouse.
{{
    config(
        materialized = 'incremental',
        unique_key = ['codigo_boleto', 'dt_referencia'],
        incremental_strategy = 'merge',
        merge_exclude_columns = ['criado_em'],
        on_schema_change = 'fail',
    )
}}

with delinquency as (

    select * from {{ ref('stg_sga__delinquency') }}

), customer_versions as (

    select codigo_associado, sk_customer, valido_de, valido_ate
    from {{ ref('dim_customers') }}

)

select
    d.codigo_associado,
    d.nome_associado,
    d.cpf_associado,
    d.codigo_situacao_associado,
    d.descricao_situacao_associado,
    d.codigo_regional_associado,
    d.nome_regional_associado,
    d.codigo_boleto,
    d.nosso_numero,
    d.codigo_situacao_boleto,
    d.descricao_situacao_boleto,
    d.pago,
    d.codigo_regional,
    d.nome_regional_boleto,
    d.mes_referente,
    d.data_emissao,
    d.data_vencimento_original,
    d.data_vencimento,
    d.valor_boleto,
    d.data_pagamento,
    d.valor_pagamento,
    d.data_credito_banco,
    d.referente,
    d.codigo_mgfformapagamento,
    d.codigo_forma_pagamento,
    d.descricao_forma_pagamento,
    d.tarifa_cobranca_banco,
    d.parcela_paga,
    d.qtde_parcela,
    d.descricao_tipo_cobranca_recorrente,
    d.codigo_tipo_boleto,
    d.descricao_tipo_boleto,
    d.codigo_conta,
    d.codigo_banco,
    d.nome_banco,
    d.agencia,
    d.conta,
    d.descricao_tipo_baixa_boleto,
    d.veiculo,
    d.beneficiario,
    d.codigo_situacao,

    -- The grain's second key. Taken from the extraction rather than the run
    -- date, which is the debt the legacy dt_referencia carries.
    (d._extracted_at at time zone 'America/Sao_Paulo')::date as dt_referencia,

    -- calculate_days_overdue, floored at zero. Note the difference from
    -- fact_invoices: there the measure is cleared once an invoice is paid, here
    -- it is not. A snapshot records how overdue the invoice was on that day,
    -- and a later payment does not change what was true then.
    case
        when d.data_vencimento is null then null
        else greatest(current_date - d.data_vencimento, 0)
    end as dias_em_atraso,

    case
        when d.data_vencimento is null then null
        when greatest(current_date - d.data_vencimento, 0) <= 30 then '0-30'
        when greatest(current_date - d.data_vencimento, 0) <= 60 then '31-60'
        when greatest(current_date - d.data_vencimento, 0) <= 90 then '61-90'
        else '90+'
    end as faixa_atraso,

    v.sk_customer,

    {{ dbt.current_timestamp() }} as criado_em,

    d.controle_carne,
    d.parcelado

from delinquency d
left join customer_versions v
    on v.codigo_associado = d.codigo_associado
   and d.data_emissao >= v.valido_de
   and (v.valido_ate is null or d.data_emissao < v.valido_ate)
