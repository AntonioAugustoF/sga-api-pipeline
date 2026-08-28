-- Materialized as a table, overriding the project default of view: dimensions
-- are consumed by Power BI, and a view would re-run the whole staging chain on
-- every visual refresh.
-- Incremental for the reason spelled out in dim_regionals: the legacy path
-- accumulates and never deletes, so rebuilding from current state would drop
-- whatever the API stops returning.
{{
    config(
        materialized = 'incremental',
        unique_key = 'codigo_cooperativa',
        incremental_strategy = 'merge',
        merge_exclude_columns = ['criado_em'],
        on_schema_change = 'fail',
    )
}}

with from_source as (

    select
        codigo_cooperativa, nome, valor_pagamento, logradouro, numero,
        complemento, bairro, cidade, estado, cep, email, cpf, contato,
        telefone, valor_pagamento_residual, telefone_comercial,
        formato_pagamento_residual, formato_pagamento, situacao,
        situacao_origem, _extracted_at
    from {{ ref('stg_sga__cooperatives') }}

), inferred as (

    select
        codigo_cooperativa, nome,
        null::double precision as valor_pagamento,
        null::text as logradouro, null::text as numero, null::text as complemento,
        null::text as bairro, null::text as cidade, null::text as estado,
        null::text as cep, null::text as email, null::text as cpf,
        null::text as contato, null::text as telefone,
        null::double precision as valor_pagamento_residual,
        null::text as telefone_comercial,
        null::text as formato_pagamento_residual, null::text as formato_pagamento,
        situacao, situacao_origem,
        (select max(_extracted_at) from {{ ref('stg_sga__cooperatives') }}) as _extracted_at
    from {{ ref('int_cooperatives_inferred') }}

), combined as (
    select * from from_source
    union all
    select * from inferred

)

select
    codigo_cooperativa,
    nome,
    valor_pagamento,
    logradouro,
    numero,
    complemento,
    bairro,
    cidade,
    estado,
    cep,
    email,
    cpf,
    contato,
    telefone,
    valor_pagamento_residual,
    telefone_comercial,
    formato_pagamento_residual,
    formato_pagamento,
    situacao,
    situacao_origem,

    -- Every final table carries audit columns. Only criado_em is
    -- emitted here: the table is fully rebuilt on every run, so there is no
    -- created-versus-updated distinction to record. That distinction becomes
    -- real in phase 3, where snapshots track it per version.
    {{  dbt.current_timestamp() }} as criado_em,

    -- Derived from the data rather than from the run date, which is  the debt
    -- the legacy data_referencia carries. The zone is explicit because
    -- _extracted_at is stored in UTC and a bare ::date would resolve against
    -- the session TimeZone, so the same batch could land on two different
    -- dates depending on who queries it.
    (_extracted_at at time zone 'America/Sao_Paulo')::date as data_referencia

from combined