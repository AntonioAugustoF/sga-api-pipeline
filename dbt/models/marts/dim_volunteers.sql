-- Incremental for the reason spelled out in dim_regionals: the legacy path
-- accumulates and never deletes, so rebuilding from current state would drop
-- whatever the API stops returning.
{{
    config(
        materialized = 'incremental',
        unique_key = 'codigo_voluntario',
        incremental_strategy = 'merge',
        merge_exclude_columns = ['criado_em'],
        on_schema_change = 'fail',
    )
}}

select
    codigo_voluntario,
    nome,
    cpf,
    cep,
    telefone,
    telefone_comercial,
    celular,
    email,
    situacao,
    codigo_classificacao,
    logradouro,
    numero,
    complemento,
    bairro,
    cidade,
    estado,
    data_cadastro,
    data_nascimento,
    cooperativas,
    situacao_origem,

    {{ dbt.current_timestamp() }} as criado_em,
    (_extracted_at at time zone 'America/Sao_Paulo')::date as data_referencia

from {{ ref('stg_sga__volunteers') }}
