-- Same contract as the vehicles test. The three date columns are excluded for
-- the reason recorded in assert_customer_dates_are_plausible: the source holds
-- impossible dates that pandas turned into NULL and these models preserve.

{{ assert_matches_legacy_where_both('dim_customers', 'dim_customers', 'vigente', 'vigente', [
    'codigo_associado', 'codigo_situacao', 'nome', 'sexo', 'tipo_pessoa',
    'rg_associado', 'cnh', 'categoria_cnh', 'dia_vencimento', 'cpf', 'ddd',
    'telefone', 'filhos', 'codigo_profissao', 'codigo_classificacao',
    'ddd_celular', 'telefone_celular', 'email', 'cep', 'logradouro', 'numero',
    'complemento', 'bairro', 'cidade', 'estado', 'data_cadastro_associado',
    'data_contrato_associado', 'codigo_regional', 'codigo_cooperativa',
    'codigo_voluntario', 'descricao_situacao',
    'valido_de', 'valido_ate'
]) }}
