{{ config(materialized = 'table') }}

select
    codigo_situacao_boleto,
    descricao_situacao_boleto,
    considerado_inadimplencia,
    pago,

    {{ dbt.current_timestamp() }} as criado_em,
    (_extracted_at at time zone 'America/Sao_Paulo')::date as data_referencia

from {{ ref('stg_sga__invoice_statuses') }}
