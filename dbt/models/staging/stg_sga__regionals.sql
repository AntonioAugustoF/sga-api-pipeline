-- Flattens the latest raw batch and applies the same normalisation the pandas
-- path applies in transform/transform_regionals.py: strip then lowercase,
-- preserving nulls as nulls and empty strings as empty strings.
--
-- website and situacao_origem are deliberately left untouched. They are absent
-- from STR_COLS in the pandas version, so normalising them here would silently
-- break reconciliation against public.dim_regionals.

with latest_batch as (

    select
        payload,
        _extracted_at
    from {{ source('sga', 'regionals') }}
    where _extracted_at = (select max(_extracted_at) from {{ source('sga','regionals') }})

)

select
    -- btrim is given the explicit character set because Python's str.strip()
    -- removes every whitespace character, while btrim defaults to spaces only.
    lower(btrim(payload ->> 'codigo_regional', E' \t\n\r\f\v')) as codigo_regional,
    lower(btrim(payload ->> 'nome',            E' \t\n\r\f\v')) as nome,
    lower(btrim(payload ->> 'nome_fantasia',   E' \t\n\r\f\v')) as nome_fantasia,
    lower(btrim(payload ->> 'cnpj',            E' \t\n\r\f\v')) as cnpj,
    lower(btrim(payload ->> 'logradouro',      E' \t\n\r\f\v')) as logradouro,
    lower(btrim(payload ->> 'numero',          E' \t\n\r\f\v')) as numero,
    lower(btrim(payload ->> 'complemento',     E' \t\n\r\f\v')) as complemento,
    lower(btrim(payload ->> 'bairro',          E' \t\n\r\f\v')) as bairro,
    lower(btrim(payload ->> 'cidade',          E' \t\n\r\f\v')) as cidade,
    lower(btrim(payload ->> 'estado',          E' \t\n\r\f\v')) as estado,
    lower(btrim(payload ->> 'cep',             E' \t\n\r\f\v')) as cep,
    lower(btrim(payload ->> 'email',           E' \t\n\r\f\v')) as email,
    lower(btrim(payload ->> 'telefone',        E' \t\n\r\f\v')) as telefone,
    lower(btrim(payload ->> 'situacao',        E' \t\n\r\f\v')) as situacao,

    payload ->> 'website'         as website,
    payload ->> 'situacao_origem' as situacao_origem,

    _extracted_at
    from latest_batch