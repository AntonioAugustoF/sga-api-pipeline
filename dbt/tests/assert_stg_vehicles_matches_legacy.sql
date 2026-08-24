-- Phase 3a: the staging model must reproduce the current version of every
-- vehicle exactly, column for column. This is what makes the snapshot safe to
-- start: if a monitored column were normalised differently here, the first
-- dbt snapshot run would read a change on all 17,949 vehicles and open that
-- many spurious versions.
--
-- Only current versions are compared. Closed versions describe the past, which
-- the API no longer returns.
--
-- campos_opcionais is deliberately excluded. The pandas path calls str() on a
-- Python list and stores the repr, so the warehouse holds
-- ['sem campo opcional cadastrado'] with single quotes. This model emits real
-- JSON. The difference is a leaked repr, not a chosen format, and reproducing
-- it would carry the defect forward. The column is not monitored, so it has no
-- effect on SCD2 versioning.

{{ assert_matches_legacy_where('stg_sga__vehicles', 'dim_vehicles', 'vigente', [
    'codigo_veiculo', 'placa', 'chassi', 'renavam', 'codigo_associado',
    'codigo_usuario', 'codigo_tipo', 'codigo_classificacao', 'codigo_cota',
    'codigo_fipe', 'valor_fipe', 'valor_fipe_protegido', 'valor_fixo', 'pontos',
    'data_reativacao', 'data_alteracao', 'codigo_depreciacao',
    'codigo_tipo_envio_boleto', 'codigo_regional', 'codigo_cooperativa',
    'codigo_marca', 'codigo_modelo', 'ano_fabricacao', 'ano_modelo',
    'codigo_combustivel', 'codigo_cor', 'codigo_grupo_produto',
    'codigo_vencimento', 'boleto_fisico', 'mes_final_carne', 'mes_referente',
    'valor_adesao', 'codigo_categoria', 'tipo', 'categoria', 'marca', 'modelo',
    'nome_associado', 'rg_associado', 'cpf_associado', 'telefone', 'ddd',
    'telefone_celular', 'ddd_celular', 'email', 'codigo_situacao',
    'descricao_situacao', 'data_cadastro', 'data_contrato', 'codigo_voluntario',
    'nome_voluntario', 'cpf_voluntario'
]) }}
