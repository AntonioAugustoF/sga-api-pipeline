with latest_batch as (

    select payload, _extracted_at
    from {{ source('sga', 'statuses') }}
    where _extracted_at = (select max(_extracted_at) from {{ source('sga', 'statuses') }})

)

select
    {{ clean_json_string('codigo_situacao') }}    as codigo_situacao,
    {{ clean_json_string('descricao_situacao') }} as descricao_situacao,
    {{ clean_json_string('cor_linha') }}          as cor_linha,
    {{ clean_json_string('cor_fonte') }}          as cor_fonte,

    -- "situacao" flags whether the status itself is still in use by the source
    -- system, not whether the customer or vehicle carrying it is active. The
    -- pandas path converts it to a boolean and drops the text column.
    case
        when payload ->> 'situacao' is null then null
        else {{ clean_json_string('situacao') }} in ('ativo')
    end as situacao_ativa,

    _extracted_at
from latest_batch