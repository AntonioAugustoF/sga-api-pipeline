with latest_batch as (

    select payload, _extracted_at
    from {{ source('sga', 'invoice_statuses') }}
        where _extracted_at = (select max(_extracted_at) from {{ source('sga', 'invoice_statuses') }})

)

select
    -- The source spells these codigo_situacaoboleto and descricao; the pandas
    -- path renames them before anything else touches the frame.
    {{ clean_json_string('codigo_situacaoboleto') }} as codigo_situacao_boleto,
    {{ clean_json_string('descricao') }}             as descricao_situacao_boleto,

    -- The API is inconsistent across domains, so all three spellings count as
    -- true. Compared after lowercasing, as the pandas helper does.
    case
        when payload ->> 'considerado_inadimplencia' is null then null
        else {{ clean_json_string('considerado_inadimplencia') }} in ('y', 's', 'sim')
    end as considerado_inadimplencia,

    case
        when payload ->> 'pago' is null then null
        else {{ clean_json_string('pago') }} in ('y', 's', 'sim')
    end as pago,

    _extracted_at
from latest_batch