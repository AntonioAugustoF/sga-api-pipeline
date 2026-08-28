-- One row per vehicle in the most recent extraction batch, normalised exactly as
-- transform/transform_vehicles.py normalises it. Generated from the column list
-- of public.dim_vehicles and the STR_COLS / DATE_COLS / numeric lists in that
-- module, so the two stay comparable column by column.
--
-- Columns absent from every list are passed through untouched, matching pandas:
-- codigo_tipo_envio_boleto.

with latest_batch as (

    -- The latest known row for every key ever seen, not the keys in the
    -- latest batch. load_dimensions.py upserts and never deletes, so the
    -- legacy dimension keeps a member the API has stopped returning; a
    -- max(_extracted_at) filter would drop it, and the snapshot version
    -- would survive with every descriptive attribute null.
    select distinct on (payload ->> 'codigo_veiculo')
        payload,
        _extracted_at
    from {{ source('sga', 'vehicles') }}
    order by payload ->> 'codigo_veiculo', _extracted_at desc

)

select
    {{ clean_json_string('codigo_veiculo') }}           as codigo_veiculo,
    {{ clean_json_string('placa') }}                    as placa,
    {{ clean_json_string('chassi') }}                   as chassi,
    {{ clean_json_string('renavam') }}                  as renavam,
    {{ clean_json_string('codigo_associado') }}         as codigo_associado,
    {{ clean_json_string('codigo_usuario') }}           as codigo_usuario,
    {{ clean_json_string('codigo_tipo') }}              as codigo_tipo,
    {{ clean_json_string('codigo_classificacao') }}     as codigo_classificacao,
    {{ clean_json_string('codigo_cota') }}              as codigo_cota,
    {{ clean_json_string('codigo_fipe') }}              as codigo_fipe,
    {{ try_json_cast('valor_fipe', 'double precision') }}               as valor_fipe,
    {{ clean_json_string('valor_fipe_protegido') }}     as valor_fipe_protegido,
    {{ try_json_cast('valor_fixo', 'double precision') }}               as valor_fixo,
    {{ try_json_cast('pontos', 'bigint') }}                   as pontos,
    {{ try_json_cast('data_reativacao', 'date') }}          as data_reativacao,
    {{ try_json_cast('data_alteracao', 'date') }}           as data_alteracao,
    {{ clean_json_string('codigo_depreciacao') }}       as codigo_depreciacao,
    payload ->> 'codigo_tipo_envio_boleto' as codigo_tipo_envio_boleto,
    {{ clean_json_string('codigo_regional') }}          as codigo_regional,
    {{ clean_json_string('codigo_cooperativa') }}       as codigo_cooperativa,
    {{ clean_json_string('codigo_marca') }}             as codigo_marca,
    {{ clean_json_string('codigo_modelo') }}            as codigo_modelo,
    {{ try_json_cast('ano_fabricacao', 'bigint') }}           as ano_fabricacao,
    {{ try_json_cast('ano_modelo', 'bigint') }}               as ano_modelo,
    {{ clean_json_string('codigo_combustivel') }}       as codigo_combustivel,
    {{ clean_json_string('codigo_cor') }}               as codigo_cor,
    {{ clean_json_string('codigo_grupo_produto') }}     as codigo_grupo_produto,
    {{ clean_json_string('codigo_vencimento') }}        as codigo_vencimento,
    {{ clean_json_string('boleto_fisico') }}            as boleto_fisico,
    {{ try_json_cast('mes_final_carne', 'bigint') }}          as mes_final_carne,
    {{ clean_json_string('mes_referente') }}            as mes_referente,
    {{ try_json_cast('valor_adesao', 'double precision') }}             as valor_adesao,
    {{ clean_json_string('codigo_categoria') }}         as codigo_categoria,
    {{ clean_json_string('tipo') }}                     as tipo,
    {{ clean_json_string('categoria') }}                as categoria,
    {{ clean_json_string('marca') }}                    as marca,
    {{ clean_json_string('modelo') }}                   as modelo,
    {{ clean_json_string('nome_associado') }}           as nome_associado,
    {{ clean_json_string('rg_associado') }}             as rg_associado,
    {{ clean_json_string('cpf_associado') }}            as cpf_associado,
    {{ clean_json_string('telefone') }}                 as telefone,
    {{ clean_json_string('ddd') }}                      as ddd,
    {{ clean_json_string('telefone_celular') }}         as telefone_celular,
    {{ clean_json_string('ddd_celular') }}              as ddd_celular,
    {{ clean_json_string('email') }}                    as email,
    {{ clean_json_string('codigo_situacao') }}          as codigo_situacao,
    {{ clean_json_string('descricao_situacao') }}       as descricao_situacao,
    {{ try_json_cast('data_cadastro', 'date') }}            as data_cadastro,
    {{ try_json_cast('data_contrato', 'date') }}            as data_contrato,
    {{ clean_json_string('codigo_voluntario') }}        as codigo_voluntario,
    {{ clean_json_string('nome_voluntario') }}          as nome_voluntario,
    {{ clean_json_string('cpf_voluntario') }}           as cpf_voluntario,
    {{ clean_json_string('campos_opcionais') }}         as campos_opcionais,

    _extracted_at
from latest_batch
