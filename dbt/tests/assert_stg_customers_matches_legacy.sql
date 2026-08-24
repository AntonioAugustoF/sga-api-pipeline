-- Phase 3a: the staging model must reproduce the current version of every
-- customer exactly, column for column. This is what makes the snapshot safe to
-- start: if a monitored column were normalised differently here, the first
-- dbt snapshot run would read a change on all 11,101 customers and open that
-- many spurious versions.
--
-- Only current versions are compared. Closed versions describe the past, which
-- the API no longer returns.
--
-- data_nascimento, data_vencimento_habilitacao and idade are excluded, and the
-- reason is a data-quality finding rather than a modelling difference. The
-- source holds impossible dates — birth years like 2972 and 9975, and birth
-- dates in the future. pandas' datetime64[ns] spans only 1677 to 2262, so
-- to_datetime(errors="coerce") turned the out-of-range ones into NULL and the
-- warehouse never showed them; the future ones survived as a negative age that
-- Python and Postgres round in opposite directions.
--
-- This model keeps what the source actually said, and
-- assert_customer_dates_are_plausible reports it. None of the three columns is
-- monitored, so none affects SCD2 versioning.

{{ assert_matches_legacy_where('stg_sga__customers', 'dim_customers', 'vigente', [
    'codigo_associado', 'codigo_situacao', 'nome', 'sexo', 'tipo_pessoa',
    'rg_associado', 'cnh', 'categoria_cnh',
    'dia_vencimento', 'cpf', 'ddd', 'telefone',
    'filhos', 'codigo_profissao', 'codigo_classificacao', 'ddd_celular',
    'telefone_celular', 'email', 'cep', 'logradouro', 'numero', 'complemento',
    'bairro', 'cidade', 'estado', 'data_cadastro_associado',
    'data_contrato_associado', 'codigo_regional', 'codigo_cooperativa',
    'codigo_voluntario', 'descricao_situacao'
]) }}
