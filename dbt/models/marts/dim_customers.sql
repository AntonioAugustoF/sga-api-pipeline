-- dim_customers as a Type 2 dimension over the snapshot, replacing the table
-- load/scd2.py maintains in public.
--
-- A mixed dimension on purpose. The 5 monitored columns come from the snapshot
-- and are versioned: a change opens a new row and past facts keep resolving to
-- the responsible party of the time. Every descriptive attribute is joined from
-- current state instead, which makes it Type 1 — the same value on every version
-- of a key. Versioning an address was never the intent, and doing so would
-- multiply the dimension for changes nobody attributes revenue by.
--
-- A consequence worth stating: on a closed version the descriptive columns show
-- today's values, not the values as of the day it closed. public.dim_customers
-- froze them instead. Reconciliation therefore compares descriptive columns on
-- current versions only; the timeline and the monitored columns are compared in
-- full by the snapshot tests.
{{ config(materialized = 'table') }}

with versions as (

    select
        *,
        row_number() over (partition by codigo_associado order by dbt_valid_from) as numero_versao
    from {{ ref('snap_customers') }}

), current_attributes as (

    -- A key present in the snapshot but absent from the latest extraction gets
    -- null descriptive attributes. There are none today, and the snapshot is
    -- configured with hard_deletes = 'ignore', so such a key would be one the
    -- source stopped returning entirely.
    select * from {{ ref('stg_sga__customers') }}

)

select
    v.codigo_associado,
    v.codigo_situacao,
    a.nome,
    a.sexo,
    a.tipo_pessoa,
    a.data_nascimento,
    a.rg_associado,
    a.cnh,
    a.categoria_cnh,
    a.data_vencimento_habilitacao,
    a.dia_vencimento,
    a.cpf,
    a.ddd,
    a.telefone,
    a.filhos,
    a.codigo_profissao,
    v.codigo_classificacao,
    a.ddd_celular,
    a.telefone_celular,
    a.email,
    a.cep,
    a.logradouro,
    a.numero,
    a.complemento,
    a.bairro,
    a.cidade,
    a.estado,
    a.data_cadastro_associado,
    a.data_contrato_associado,
    v.codigo_regional,
    v.codigo_cooperativa,
    v.codigo_voluntario,
    a.descricao_situacao,
    a.idade,

    -- The snapshot's own id is the surrogate key: a deterministic hash of the
    -- natural key and the version's start, already unique and already the
    -- primary key of the snapshot table. This replaces the SERIAL sk_customer,
    -- which could not survive a rebuild — and it is the one change in this
    -- migration visible outside the repository, since Power BI has to rebuild
    -- the relationship once.
    v.dbt_scd_id as sk_customer,

    -- The first version of a key reaches back to the epoch so that facts
    -- predating its discovery still resolve to it. dbt stamps dbt_valid_from at
    -- the moment it first saw the key, so without this a vehicle first seen
    -- today would cover no invoice issued before today, and the revenue would
    -- vanish from point-in-time attribution.
    case
        when v.numero_versao = 1 then date '1900-01-01'
        else v.dbt_valid_from::date
    end as valido_de,

    v.dbt_valid_to::date       as valido_ate,
    v.dbt_valid_to is null     as vigente,

    {{ dbt.current_timestamp() }} as criado_em

from versions v
left join current_attributes a
    on a.codigo_associado = v.codigo_associado
