-- Materialized as a table, overrding the project default of the view: this
-- dimension is consumed by Power BI, and a view would re-run the whole staging
-- chain on every visual refresh.
{{ config(materialized = 'table') }}

select
    codigo_regional,
    nome,
    nome_fantasia,
    cnpj,
    logradouro,
    numero,
    complemento,
    bairro,
    cidade,
    estado,
    cep,
    email,
    website,
    telefone,
    situacao,
    situacao_origem,

    -- Audit columns required by section 3.4 of CLAUDE.md. Only criado_em is
    -- emitted: the table is fully rebuilt on every run, so there is no
    -- created-versus-updated distinction to record. That distinction becomes
    -- real in phase 3, where snapshots track it per version.
    {{ dbt.current_timestamp() }} as criado_em,

    -- Derived from the data rather than from the run date, which is the debt
    -- that the legacy data_referencia carries. The zone is explicit because
    -- _extracted_at is stored  in UTC and a bare ::date would resolve against
    -- the session TimeZone, so the same batch could land on two different
    -- dates depending on who queries it.
    (_extracted_at at time zone 'America/Sao_Paulo')::date as data_referencia

    from {{ ref('stg_sga__regionals') }}