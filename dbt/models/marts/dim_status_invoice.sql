-- Incremental for the reason spelled out in dim_regionals: the legacy path
-- accumulates and never deletes, so rebuilding from current state would drop
-- whatever the API stops returning.
{{
    config(
        materialized = 'incremental',
        unique_key = 'codigo_situacao_boleto',
        incremental_strategy = 'merge',
        merge_exclude_columns = ['criado_em'],
        on_schema_change = 'fail',
    )
}}

select
    codigo_situacao_boleto,
    descricao_situacao_boleto,
    considerado_inadimplencia,
    pago,

    {{ dbt.current_timestamp() }} as criado_em,
    (_extracted_at at time zone 'America/Sao_Paulo')::date as data_referencia

from {{ ref('stg_sga__invoice_statuses') }}
