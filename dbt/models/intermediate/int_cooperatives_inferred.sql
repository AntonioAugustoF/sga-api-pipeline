-- Cooperatives referenced by a customer or a vehicle but the absent from the API
-- response. The pandas path has no rule for this: the two rows currently in
-- public.dim_cooperatives were inserted by hand to unblock a foreign key, carry
-- null audit columns and an unnormalised name, and no code reproduces them.
-- Rebuilding the warehouse from the baseline would break the constraint.
--
-- This model turns that manual patch into a derived rule. It reads the raw
-- sources directly beacuse costumers and vehicles only reach staging in phase
-- 3; repoint  these to ref() then.

with from_api as (

    select payload ->> 'codigo_cooperativa' as codigo_cooperativa
    from {{ source('sga', 'cooperatives') }}
    where _extracted_at = (select max(_extracted_at) from {{ source('sga', 'cooperatives') }})

), referenced as (

    select distinct payload ->> 'codigo_cooperativa' as codigo_cooperativa
    from {{ source('sga', 'customers') }}
    where _extracted_at = (select max(_extracted_at) from {{ source('sga', 'customers') }})

    union

    select distinct payload ->> 'codigo_cooperativa'
    from {{ source('sga', 'vehicles') }}
    where _extracted_at = (select max(_extracted_at) from {{ source('sga', 'vehicles')}})

)

select
    referenced.codigo_cooperativa,

    -- Reproduced verbatim, capital letter included, because the legacy rows were
    -- written outside cast_string_columns and reconciliation compares exact
    -- strings. Normalise this at cutover, not before.
    'Cooperativa excluida da base' as nome,
    'excluido'                     as situacao,
    'inferido'                     as situacao_origem

    from referenced
    left join from_api using (codigo_cooperativa)
    where from_api.codigo_cooperativa is null
      and referenced.codigo_cooperativa is not null