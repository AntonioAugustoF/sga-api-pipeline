-- One row per volunteer in the most recent extraction batch, normalised as
-- transform/transform_volunteers.py normalises it.
--
-- This is the one entity whose COLS_TO_DROP is actually applied — in
-- transform_regionals and transform_cooperatives the list is declared and never
-- used. formato_pagamento, formato_pagamento_residual, valor_pagamento,
-- valor_pagamento_residual and obs are therefore absent here as well.

with latest_batch as (

    select payload, _extracted_at
    from {{ source('sga', 'volunteers') }}
    where _extracted_at = (select max(_extracted_at) from {{ source('sga', 'volunteers') }})

)

select
    {{ clean_json_string('codigo_voluntario') }}     as codigo_voluntario,
    {{ clean_json_string('nome') }}                  as nome,
    {{ clean_json_string('cpf') }}                   as cpf,
    {{ clean_json_string('cep') }}                   as cep,
    {{ clean_json_string('telefone') }}              as telefone,
    {{ clean_json_string('telefone_comercial') }}    as telefone_comercial,
    {{ clean_json_string('celular') }}               as celular,
    {{ clean_json_string('email') }}                 as email,
    {{ clean_json_string('situacao') }}              as situacao,
    {{ clean_json_string('codigo_classificacao') }}  as codigo_classificacao,
    {{ clean_json_string('logradouro') }}            as logradouro,
    {{ clean_json_string('numero') }}                as numero,
    {{ clean_json_string('complemento') }}           as complemento,
    {{ clean_json_string('bairro') }}                as bairro,
    {{ clean_json_string('cidade') }}                as cidade,
    {{ clean_json_string('estado') }}                as estado,

    {{ try_json_cast('data_cadastro', 'date') }}     as data_cadastro,
    {{ try_json_cast('data_nascimento', 'date') }}   as data_nascimento,

    -- The source sends a list of objects; the pandas path keeps only
    -- codigo_cooperativa from each and joins them with a comma. Ordinality
    -- preserves the source order, which string_agg would otherwise be free to
    -- ignore. An empty list becomes an empty string rather than null, matching
    -- "".join([]) — a volunteer with no cooperative is not a volunteer with an
    -- unknown one.
    case
        when jsonb_typeof(payload -> 'cooperativas') <> 'array' then null
        else coalesce(
            (
                select string_agg(c.value ->> 'codigo_cooperativa', ',' order by c.ord)
                from jsonb_array_elements(payload -> 'cooperativas') with ordinality as c(value, ord)
            ),
            ''
        )
    end as cooperativas,

    -- In this entity situacao_origem is inside STR_COLS, unlike every other
    -- one, so it is normalised here and not passed through.
    {{ clean_json_string('situacao_origem') }}       as situacao_origem,

    _extracted_at
from latest_batch
