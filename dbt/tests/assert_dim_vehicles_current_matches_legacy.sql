-- Phase 3c: the current version of every vehicle must match the one
-- load/scd2.py maintains, across both the versioned and the descriptive columns.
--
-- Current versions only. This dimension is mixed: descriptive attributes are
-- Type 1, so on a closed version they carry today's values while
-- public.dim_vehicles froze them at closing time. The timeline and the eight
-- monitored columns are compared across all versions by
-- assert_snapshot_vehicles_history_matches_legacy.
--
-- campos_opcionais is excluded for the same reason as in staging: the legacy
-- value is a leaked Python repr.

{{ assert_matches_legacy_where_both('dim_vehicles', 'dim_vehicles', 'vigente', 'vigente', [
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
    'nome_voluntario', 'cpf_voluntario',
    'valido_de', 'valido_ate'
]) }}
