-- One row per customer in the most recent extraction batch, normalised exactly as
-- transform/transform_customers.py normalises it.
--
-- Columns absent from STR_COLS and DATE_COLS are passed through untouched,
-- matching pandas: filhos.

with latest_batch as (

    -- The latest known row for every key ever seen, not the keys in the
    -- latest batch. load_dimensions.py upserts and never deletes, so the
    -- legacy dimension keeps a member the API has stopped returning; a
    -- max(_extracted_at) filter would drop it, and the snapshot version
    -- would survive with every descriptive attribute null.
    select distinct on (payload ->> 'codigo_associado')
        payload,
        _extracted_at
    from {{ source('sga', 'customers') }}
    order by payload ->> 'codigo_associado', _extracted_at desc

), status_lookup as (

    -- The pandas path maps codigo_situacao through the raw status list, not
    -- through dim_status, so descricao_situacao keeps the source's original
    -- casing. Reading stg_sga__statuses here would lowercase it and break
    -- reconciliation.
    select
        payload ->> 'codigo_situacao'    as codigo_situacao,
        payload ->> 'descricao_situacao' as descricao_situacao
    from {{ source('sga', 'statuses') }}
    where _extracted_at = (select max(_extracted_at) from {{ source('sga', 'statuses') }})

)

select
    {{ clean_json_string('codigo_associado') }}            as codigo_associado,
    {{ clean_json_string('codigo_situacao') }}             as codigo_situacao,
    {{ clean_json_string('nome') }}                        as nome,
    {{ clean_json_string('sexo') }}                        as sexo,
    {{ clean_json_string('tipo_pessoa') }}                 as tipo_pessoa,
    {{ try_json_cast('data_nascimento', 'date') }}             as data_nascimento,
    {{ clean_json_string('rg_associado') }}                as rg_associado,
    {{ clean_json_string('cnh') }}                         as cnh,
    {{ clean_json_string('categoria_cnh') }}               as categoria_cnh,
    {{ try_json_cast('data_vencimento_habilitacao', 'date') }} as data_vencimento_habilitacao,
    {{ clean_json_string('dia_vencimento') }}              as dia_vencimento,
    {{ clean_json_string('cpf') }}                         as cpf,
    {{ clean_json_string('ddd') }}                         as ddd,
    {{ clean_json_string('telefone') }}                    as telefone,
    -- double precision rather than an integer, matching the legacy column:
    -- pandas has no nullable integer, so a single null promotes the whole
    -- series to float64 and that is what reached the warehouse.
    {{ try_json_cast('filhos', 'double precision') }} as filhos,
    {{ clean_json_string('codigo_profissao') }}            as codigo_profissao,
    {{ clean_json_string('codigo_classificacao') }}        as codigo_classificacao,
    {{ clean_json_string('ddd_celular') }}                 as ddd_celular,
    {{ clean_json_string('telefone_celular') }}            as telefone_celular,
    {{ clean_json_string('email') }}                       as email,
    {{ clean_json_string('cep') }}                         as cep,
    {{ clean_json_string('logradouro') }}                  as logradouro,
    {{ clean_json_string('numero') }}                      as numero,
    {{ clean_json_string('complemento') }}                 as complemento,
    {{ clean_json_string('bairro') }}                      as bairro,
    {{ clean_json_string('cidade') }}                      as cidade,
    {{ clean_json_string('estado') }}                      as estado,
    {{ try_json_cast('data_cadastro_associado', 'date') }}     as data_cadastro_associado,
    {{ try_json_cast('data_contrato_associado', 'date') }}     as data_contrato_associado,
    {{ clean_json_string('codigo_regional') }}             as codigo_regional,
    {{ clean_json_string('codigo_cooperativa') }}          as codigo_cooperativa,
    {{ clean_json_string('codigo_voluntario') }}           as codigo_voluntario,

    lookup.descricao_situacao,

    -- Age in full years, recomputed on every run against the current date, as
    -- calculate_age does. It is not a monitored column, so it refreshes in
    -- place rather than opening a new version.
    case
        when {{ try_json_cast('data_nascimento', 'date') }} is null then null
        else extract(year from age(current_date, {{ try_json_cast('data_nascimento', 'date') }}))::double precision
    end as idade,

    _extracted_at
from latest_batch
left join status_lookup lookup
    on lookup.codigo_situacao = {{ clean_json_string('codigo_situacao') }}
