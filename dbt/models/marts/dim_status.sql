-- Named after the production table rather than pluralised: at cutover this
-- becomes a schema swap, not a rename.
{{ config(materialized = 'table') }}

select
    codigo_situacao,
    descricao_situacao,
    cor_linha,
    cor_fonte,
    situacao_ativa,

    {{ dbt.current_timestamp() }} as criado_em,
    (_extracted_at at time zone 'America/Sao_Paulo')::date as data_referencia

from {{ ref('stg_sga__statuses') }}
