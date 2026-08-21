-- COLS_TO_DROP is declared in transform_cooperatives.py but never applied, so
-- every column survives into the dimension. Reproduced here on purpose: this
-- model reconcilies against what the pandas path actually produces, not against
-- what it appears to intend.

with latest_batch as (

    select payload, _extracted_at
    from {{ source('sga', 'cooperatives') }}
    where _extracted_at = (select max(_extracted_at) from {{ source('sga', 'cooperatives') }})

)

select
    {{ clean_json_string('codigo_cooperativa') }} as codigo_cooperativa,
    {{ clean_json_string('nome') }}               as nome,
    {{ clean_json_string('logradouro') }}         as logradouro,
    {{ clean_json_string('numero') }}             as numero,
    {{ clean_json_string('complemento') }}        as complemento,
    {{ clean_json_string('bairro') }}             as bairro,
    {{ clean_json_string('cidade') }}             as cidade,
    {{ clean_json_string('estado') }}             as estado,
    {{ clean_json_string('cep') }}                as cep,
    {{ clean_json_string('email') }}              as email,
    {{ clean_json_string('cpf') }}                as cpf,
    {{ clean_json_string('telefone') }}           as telefone,
    {{ clean_json_string('situacao') }}           as situacao,

    {{ try_json_cast('valor_pagamento', 'double precision') }}          as valor_pagamento,
    {{ try_json_cast('valor_pagamento_residual', 'double precision') }} as valor_pagamento_residual,

    -- Absent from STR_COLS in the pandas version, so left untouched here.
    payload ->> 'contato'                    as contato,
    payload ->> 'telefone_comercial'         as telefone_comercial,
    payload ->> 'formato_pagamento'          as formato_pagamento,
    payload ->> 'formato_pagamento_residual' as formato_pagamento_residual,
    payload ->> 'situacao_origem'            as situacao_origem,
    
    _extracted_at
from latest_batch
