-- Phase 2 correction: seed the five simple dimensions with everything the
-- pandas path accumulated.
--
-- Why this is needed at all. load_dimensions.py upserts and never deletes, so
-- public.dim_* holds every key the API has ever returned. The dbt models were
-- materialised as tables, rebuilt from current state, which is a different
-- semantics -- and the difference stayed invisible while every key was still
-- being returned.
--
-- dim_volunteers is where it surfaced. Eight volunteers are in the legacy and
-- absent from the current extraction, and four of them (23, 141, 173, 212) are
-- referenced by thirteen vehicles carrying 204 invoices. Materialising from
-- current state alone would leave that revenue attributed to nothing.
--
-- The other four dimensions had the same defect and reconciled only because
-- nothing had dropped out of their populations yet.
--
-- dim_customers and dim_vehicles are deliberately absent: they are tables too,
-- but they derive from the snapshots, where the history actually lives, so
-- rebuilding them is both cheap and correct.
--
-- Reversible: nothing writes to public. Deliberately not idempotent, except for
-- the drops below, which are needed once because the models already created
-- these tables as tables.

BEGIN;

DROP TABLE IF EXISTS analytics.dim_regionals;
DROP TABLE IF EXISTS analytics.dim_cooperatives;
DROP TABLE IF EXISTS analytics.dim_status;
DROP TABLE IF EXISTS analytics.dim_status_invoice;
DROP TABLE IF EXISTS analytics.dim_volunteers;

CREATE TABLE analytics.dim_regionals AS
SELECT
    codigo_regional,
    nome,
    nome_fantasia,
    cnpj,
    logradouro,
    numero,
    complemento,
    bairro,
    cidade,
    estado,
    cep,
    email,
    website,
    telefone,
    situacao,
    situacao_origem,
    criado_em::timestamptz as criado_em,
    data_referencia
FROM public.dim_regionals;

ALTER TABLE analytics.dim_regionals ADD PRIMARY KEY (codigo_regional);

CREATE TABLE analytics.dim_cooperatives AS
SELECT
    codigo_cooperativa,
    nome,
    valor_pagamento,
    logradouro,
    numero,
    complemento,
    bairro,
    cidade,
    estado,
    cep,
    email,
    cpf,
    contato,
    telefone,
    valor_pagamento_residual,
    telefone_comercial,
    formato_pagamento_residual,
    formato_pagamento,
    situacao,
    situacao_origem,
    criado_em::timestamptz as criado_em,
    data_referencia
FROM public.dim_cooperatives;

ALTER TABLE analytics.dim_cooperatives ADD PRIMARY KEY (codigo_cooperativa);

CREATE TABLE analytics.dim_status AS
SELECT
    codigo_situacao,
    descricao_situacao,
    cor_linha,
    cor_fonte,
    situacao_ativa,
    criado_em::timestamptz as criado_em,
    data_referencia
FROM public.dim_status;

ALTER TABLE analytics.dim_status ADD PRIMARY KEY (codigo_situacao);

CREATE TABLE analytics.dim_status_invoice AS
SELECT
    codigo_situacao_boleto,
    descricao_situacao_boleto,
    considerado_inadimplencia,
    pago,
    criado_em::timestamptz as criado_em,
    data_referencia
FROM public.dim_status_invoice;

ALTER TABLE analytics.dim_status_invoice ADD PRIMARY KEY (codigo_situacao_boleto);

CREATE TABLE analytics.dim_volunteers AS
SELECT
    codigo_voluntario,
    nome,
    cpf,
    cep,
    telefone,
    telefone_comercial,
    celular,
    email,
    situacao,
    codigo_classificacao,
    logradouro,
    numero,
    complemento,
    bairro,
    cidade,
    estado,
    data_cadastro,
    data_nascimento,
    cooperativas,
    situacao_origem,
    criado_em::timestamptz as criado_em,
    data_referencia
FROM public.dim_volunteers;

ALTER TABLE analytics.dim_volunteers ADD PRIMARY KEY (codigo_voluntario);

COMMIT;
