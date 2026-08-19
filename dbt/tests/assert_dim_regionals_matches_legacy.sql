-- Phase 1 reconciliation: the dbt dimension must be byte-for-byte identical to
-- the one thee pandas path writes. Audit columns are excluded because they are
-- expected to differ — the two paths run at different times.
--
-- EXCEPT is used rather than join because it treats NULL as equal to NULL,
-- which a join predicate does not. Both directions are checked: a row present
-- only in the legacy table is as much a failure as an extra row in dbt.

with dbt_side as (

    select codigo_regional, nome, nome_fantasia, cnpj, logradouro, numero,
           complemento, bairro, cidade, estado, cep, email, website, telefone,
           situacao, situacao_origem
    from {{ ref('dim_regionals') }}

), legacy_side as (

    select codigo_regional, nome, nome_fantasia, cnpj, logradouro, numero,
           complemento, bairro, cidade, estado, cep, email, website, telefone,
           situacao, situacao_origem
    from {{ source('warehouse', 'dim_regionals') }}

)

select 'only_in_dbt' as lado, * from (select * from dbt_side except select * from legacy_side) d
union all
select 'only_in_legacy', * from (select * from legacy_side except select * from dbt_side) l
