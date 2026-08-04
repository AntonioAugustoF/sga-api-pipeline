--
-- PostgreSQL database dump
--


-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: bridge_invoices_vehicles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bridge_invoices_vehicles (
    codigo_boleto text NOT NULL,
    codigo_veiculo text NOT NULL,
    qtd_veiculos_boleto bigint,
    valor_rateado double precision,
    criado_em timestamp without time zone,
    data_referencia date,
    atualizado_em timestamp without time zone
);


--
-- Name: dim_cooperatives; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_cooperatives (
    codigo_cooperativa text NOT NULL,
    nome text,
    valor_pagamento double precision,
    logradouro text,
    numero text,
    complemento text,
    bairro text,
    cidade text,
    estado text,
    cep text,
    email text,
    cpf text,
    contato text,
    telefone text,
    valor_pagamento_residual double precision,
    telefone_comercial text,
    formato_pagamento_residual text,
    formato_pagamento text,
    situacao text,
    situacao_origem text,
    criado_em timestamp without time zone,
    atualizado_em timestamp without time zone,
    data_referencia date
);


--
-- Name: dim_customers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_customers (
    codigo_associado text,
    codigo_situacao text,
    nome text,
    sexo text,
    tipo_pessoa text,
    data_nascimento date,
    rg_associado text,
    cnh text,
    categoria_cnh text,
    data_vencimento_habilitacao date,
    dia_vencimento text,
    cpf text,
    ddd text,
    telefone text,
    filhos double precision,
    codigo_profissao text,
    codigo_classificacao text,
    ddd_celular text,
    telefone_celular text,
    email text,
    cep text,
    logradouro text,
    numero text,
    complemento text,
    bairro text,
    cidade text,
    estado text,
    data_cadastro_associado date,
    data_contrato_associado date,
    codigo_regional text,
    codigo_cooperativa text,
    codigo_voluntario text,
    descricao_situacao text,
    idade double precision,
    valido_de date,
    valido_ate date,
    vigente boolean,
    sk_customer integer NOT NULL,
    criado_em timestamp without time zone,
    atualizado_em timestamp without time zone
);


--
-- Name: dim_customers_current; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.dim_customers_current AS
 SELECT codigo_associado,
    codigo_situacao,
    nome,
    sexo,
    tipo_pessoa,
    data_nascimento,
    rg_associado,
    cnh,
    categoria_cnh,
    data_vencimento_habilitacao,
    dia_vencimento,
    cpf,
    ddd,
    telefone,
    filhos,
    codigo_profissao,
    codigo_classificacao,
    ddd_celular,
    telefone_celular,
    email,
    cep,
    logradouro,
    numero,
    complemento,
    bairro,
    cidade,
    estado,
    data_cadastro_associado,
    data_contrato_associado,
    codigo_regional,
    codigo_cooperativa,
    codigo_voluntario,
    descricao_situacao,
    idade,
    valido_de,
    valido_ate,
    vigente,
    sk_customer
   FROM public.dim_customers
  WHERE (vigente = true);


--
-- Name: dim_customers_sk_customer_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.dim_customers_sk_customer_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dim_customers_sk_customer_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.dim_customers_sk_customer_seq OWNED BY public.dim_customers.sk_customer;


--
-- Name: dim_regionals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_regionals (
    codigo_regional text NOT NULL,
    nome text,
    nome_fantasia text,
    cnpj text,
    logradouro text,
    numero text,
    complemento text,
    bairro text,
    cidade text,
    estado text,
    cep text,
    email text,
    website text,
    telefone text,
    situacao text,
    situacao_origem text,
    criado_em timestamp without time zone,
    atualizado_em timestamp without time zone,
    data_referencia date
);


--
-- Name: dim_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_status (
    codigo_situacao text NOT NULL,
    descricao_situacao text,
    cor_linha text,
    cor_fonte text,
    situacao_ativa boolean,
    criado_em timestamp without time zone,
    atualizado_em timestamp without time zone,
    data_referencia date
);


--
-- Name: dim_status_invoice; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_status_invoice (
    codigo_situacao_boleto text NOT NULL,
    descricao_situacao_boleto text,
    considerado_inadimplencia boolean,
    pago boolean,
    criado_em timestamp without time zone,
    atualizado_em timestamp without time zone,
    data_referencia date
);


--
-- Name: dim_vehicles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_vehicles (
    codigo_veiculo text,
    placa text,
    chassi text,
    renavam text,
    codigo_associado text,
    codigo_usuario text,
    codigo_tipo text,
    codigo_classificacao text,
    codigo_cota text,
    codigo_fipe text,
    valor_fipe double precision,
    valor_fipe_protegido text,
    valor_fixo double precision,
    pontos bigint,
    data_reativacao date,
    data_alteracao date,
    codigo_depreciacao text,
    codigo_tipo_envio_boleto text,
    codigo_regional text,
    codigo_cooperativa text,
    codigo_marca text,
    codigo_modelo text,
    ano_fabricacao bigint,
    ano_modelo bigint,
    codigo_combustivel text,
    codigo_cor text,
    codigo_grupo_produto text,
    codigo_vencimento text,
    boleto_fisico text,
    mes_final_carne bigint,
    mes_referente text,
    valor_adesao double precision,
    codigo_categoria text,
    tipo text,
    categoria text,
    marca text,
    modelo text,
    nome_associado text,
    rg_associado text,
    cpf_associado text,
    telefone text,
    ddd text,
    telefone_celular text,
    ddd_celular text,
    email text,
    codigo_situacao text,
    descricao_situacao text,
    data_cadastro date,
    data_contrato date,
    codigo_voluntario text,
    nome_voluntario text,
    cpf_voluntario text,
    campos_opcionais text,
    valido_de date,
    valido_ate date,
    vigente boolean,
    sk_vehicle integer NOT NULL,
    criado_em timestamp without time zone,
    atualizado_em timestamp without time zone
);


--
-- Name: dim_vehicles_current; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.dim_vehicles_current AS
 SELECT codigo_veiculo,
    placa,
    chassi,
    renavam,
    codigo_associado,
    codigo_usuario,
    codigo_tipo,
    codigo_classificacao,
    codigo_cota,
    codigo_fipe,
    valor_fipe,
    valor_fipe_protegido,
    valor_fixo,
    pontos,
    data_reativacao,
    data_alteracao,
    codigo_depreciacao,
    codigo_tipo_envio_boleto,
    codigo_regional,
    codigo_cooperativa,
    codigo_marca,
    codigo_modelo,
    ano_fabricacao,
    ano_modelo,
    codigo_combustivel,
    codigo_cor,
    codigo_grupo_produto,
    codigo_vencimento,
    boleto_fisico,
    mes_final_carne,
    mes_referente,
    valor_adesao,
    codigo_categoria,
    tipo,
    categoria,
    marca,
    modelo,
    nome_associado,
    rg_associado,
    cpf_associado,
    telefone,
    ddd,
    telefone_celular,
    ddd_celular,
    email,
    codigo_situacao,
    descricao_situacao,
    data_cadastro,
    data_contrato,
    codigo_voluntario,
    nome_voluntario,
    cpf_voluntario,
    campos_opcionais,
    valido_de,
    valido_ate,
    vigente,
    sk_vehicle
   FROM public.dim_vehicles
  WHERE (vigente = true);


--
-- Name: dim_vehicles_sk_vehicle_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.dim_vehicles_sk_vehicle_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dim_vehicles_sk_vehicle_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.dim_vehicles_sk_vehicle_seq OWNED BY public.dim_vehicles.sk_vehicle;


--
-- Name: dim_volunteers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_volunteers (
    codigo_voluntario text NOT NULL,
    nome text,
    cpf text,
    cep text,
    telefone text,
    telefone_comercial text,
    celular text,
    email text,
    situacao text,
    codigo_classificacao text,
    logradouro text,
    numero text,
    complemento text,
    bairro text,
    cidade text,
    estado text,
    data_cadastro date,
    data_nascimento date,
    cooperativas text,
    situacao_origem text,
    criado_em timestamp without time zone,
    atualizado_em timestamp without time zone,
    data_referencia date
);


--
-- Name: fact_delinquency_snapshot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_delinquency_snapshot (
    codigo_associado text,
    nome_associado text,
    cpf_associado text,
    codigo_situacao_associado text,
    descricao_situacao_associado text,
    codigo_regional_associado text,
    nome_regional_associado text,
    codigo_boleto text NOT NULL,
    nosso_numero text,
    codigo_situacao_boleto text,
    descricao_situacao_boleto text,
    pago text,
    codigo_regional text,
    nome_regional_boleto text,
    mes_referente text,
    data_emissao date,
    data_vencimento_original date,
    data_vencimento date,
    valor_boleto double precision,
    data_pagamento text,
    valor_pagamento bigint,
    data_credito_banco text,
    referente text,
    codigo_mgfformapagamento text,
    codigo_forma_pagamento text,
    descricao_forma_pagamento text,
    tarifa_cobranca_banco double precision,
    parcela_paga bigint,
    qtde_parcela bigint,
    descricao_tipo_cobranca_recorrente text,
    codigo_tipo_boleto text,
    descricao_tipo_boleto text,
    codigo_conta text,
    codigo_banco text,
    nome_banco text,
    agencia text,
    conta text,
    descricao_tipo_baixa_boleto text,
    veiculo text,
    beneficiario text,
    codigo_situacao text,
    dt_referencia date NOT NULL,
    dias_em_atraso bigint,
    faixa_atraso text,
    sk_customer integer,
    criado_em timestamp without time zone
);


--
-- Name: fact_invoices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_invoices (
    codigo_associado text,
    nome_associado text,
    cpf_associado text,
    codigo_situacao_associado text,
    descricao_situacao_associado text,
    codigo_regional_associado text,
    nome_regional_associado text,
    codigo_boleto text NOT NULL,
    nosso_numero text,
    codigo_situacao_boleto text,
    descricao_situacao_boleto text,
    pago text,
    codigo_regional text,
    nome_regional_boleto text,
    mes_referente text,
    data_emissao date,
    data_vencimento_original date,
    data_vencimento date,
    valor_boleto double precision,
    data_pagamento date,
    valor_pagamento double precision,
    data_credito_banco date,
    referente text,
    codigo_mgfformapagamento text,
    codigo_forma_pagamento text,
    descricao_forma_pagamento text,
    tarifa_cobranca_banco double precision,
    parcela_paga bigint,
    qtde_parcela bigint,
    descricao_tipo_cobranca_recorrente text,
    codigo_tipo_boleto text,
    descricao_tipo_boleto text,
    codigo_conta text,
    codigo_banco text,
    nome_banco text,
    agencia text,
    conta text,
    descricao_tipo_baixa_boleto text,
    veiculo text,
    beneficiario text,
    codigo_situacao text,
    dias_em_atraso double precision,
    faixa_atraso text,
    status_pagamento text,
    diferenca_pagamento double precision,
    sk_customer integer,
    criado_em timestamp without time zone,
    atualizado_em timestamp without time zone,
    data_referencia date
);


--
-- Name: vw_delinquency_by_vehicle_atual; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vw_delinquency_by_vehicle_atual AS
 SELECT f.codigo_boleto,
    f.dt_referencia,
    f.data_emissao,
    f.data_vencimento,
    f.valor_boleto,
    f.dias_em_atraso,
    f.faixa_atraso,
    f.pago,
    b.codigo_veiculo,
    b.qtd_veiculos_boleto,
    (f.valor_boleto / (b.qtd_veiculos_boleto)::double precision) AS valor_rateado,
    v.codigo_voluntario,
    v.nome_voluntario,
    v.codigo_regional AS codigo_regional_veiculo,
    v.codigo_cooperativa AS codigo_cooperativa_veiculo,
    v.codigo_situacao AS codigo_situacao_veiculo
   FROM ((public.fact_delinquency_snapshot f
     LEFT JOIN public.bridge_invoices_vehicles b ON ((b.codigo_boleto = f.codigo_boleto)))
     LEFT JOIN public.dim_vehicles_current v ON ((v.codigo_veiculo = b.codigo_veiculo)));


--
-- Name: vw_delinquency_by_vehicle_historico; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vw_delinquency_by_vehicle_historico AS
 SELECT f.codigo_boleto,
    f.dt_referencia,
    f.data_emissao,
    f.data_vencimento,
    f.valor_boleto,
    f.dias_em_atraso,
    f.faixa_atraso,
    f.pago,
    b.codigo_veiculo,
    b.qtd_veiculos_boleto,
    (f.valor_boleto / (b.qtd_veiculos_boleto)::double precision) AS valor_rateado,
    v.sk_vehicle,
    v.codigo_voluntario,
    v.nome_voluntario,
    v.codigo_regional AS codigo_regional_veiculo,
    v.codigo_cooperativa AS codigo_cooperativa_veiculo,
    v.codigo_situacao AS codigo_situacao_veiculo
   FROM ((public.fact_delinquency_snapshot f
     LEFT JOIN public.bridge_invoices_vehicles b ON ((b.codigo_boleto = f.codigo_boleto)))
     LEFT JOIN public.dim_vehicles v ON (((v.codigo_veiculo = b.codigo_veiculo) AND (f.dt_referencia >= v.valido_de) AND ((v.valido_ate IS NULL) OR (f.dt_referencia < v.valido_ate)))));


--
-- Name: dim_customers sk_customer; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_customers ALTER COLUMN sk_customer SET DEFAULT nextval('public.dim_customers_sk_customer_seq'::regclass);


--
-- Name: dim_vehicles sk_vehicle; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_vehicles ALTER COLUMN sk_vehicle SET DEFAULT nextval('public.dim_vehicles_sk_vehicle_seq'::regclass);


--
-- Name: bridge_invoices_vehicles bridge_invoices_vehicles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bridge_invoices_vehicles
    ADD CONSTRAINT bridge_invoices_vehicles_pkey PRIMARY KEY (codigo_boleto, codigo_veiculo);


--
-- Name: dim_cooperatives dim_cooperatives_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_cooperatives
    ADD CONSTRAINT dim_cooperatives_pkey PRIMARY KEY (codigo_cooperativa);


--
-- Name: dim_customers dim_customers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_customers
    ADD CONSTRAINT dim_customers_pkey PRIMARY KEY (sk_customer);


--
-- Name: dim_regionals dim_regionals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_regionals
    ADD CONSTRAINT dim_regionals_pkey PRIMARY KEY (codigo_regional);


--
-- Name: dim_status_invoice dim_status_invoice_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_status_invoice
    ADD CONSTRAINT dim_status_invoice_pkey PRIMARY KEY (codigo_situacao_boleto);


--
-- Name: dim_status dim_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_status
    ADD CONSTRAINT dim_status_pkey PRIMARY KEY (codigo_situacao);


--
-- Name: dim_vehicles dim_vehicles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_vehicles
    ADD CONSTRAINT dim_vehicles_pkey PRIMARY KEY (sk_vehicle);


--
-- Name: dim_volunteers dim_volunteers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_volunteers
    ADD CONSTRAINT dim_volunteers_pkey PRIMARY KEY (codigo_voluntario);


--
-- Name: fact_delinquency_snapshot fact_delinquency_snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_delinquency_snapshot
    ADD CONSTRAINT fact_delinquency_snapshot_pkey PRIMARY KEY (codigo_boleto, dt_referencia);


--
-- Name: fact_invoices fact_invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_invoices
    ADD CONSTRAINT fact_invoices_pkey PRIMARY KEY (codigo_boleto);


--
-- Name: dim_customers uq_dim_customers_nk_validade; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_customers
    ADD CONSTRAINT uq_dim_customers_nk_validade UNIQUE (codigo_associado, valido_de);


--
-- Name: dim_vehicles uq_dim_vehicles_nk_validade; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_vehicles
    ADD CONSTRAINT uq_dim_vehicles_nk_validade UNIQUE (codigo_veiculo, valido_de);


--
-- Name: idx_delinquency_codigo_associado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_delinquency_codigo_associado ON public.fact_delinquency_snapshot USING btree (codigo_associado);


--
-- Name: idx_delinquency_sk_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_delinquency_sk_customer ON public.fact_delinquency_snapshot USING btree (sk_customer);


--
-- Name: idx_dim_customers_codigo_cooperativa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dim_customers_codigo_cooperativa ON public.dim_customers USING btree (codigo_cooperativa);


--
-- Name: idx_dim_customers_codigo_regional; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dim_customers_codigo_regional ON public.dim_customers USING btree (codigo_regional);


--
-- Name: idx_dim_customers_codigo_voluntario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dim_customers_codigo_voluntario ON public.dim_customers USING btree (codigo_voluntario);


--
-- Name: idx_dim_vehicles_codigo_cooperativa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dim_vehicles_codigo_cooperativa ON public.dim_vehicles USING btree (codigo_cooperativa);


--
-- Name: idx_dim_vehicles_codigo_regional; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dim_vehicles_codigo_regional ON public.dim_vehicles USING btree (codigo_regional);


--
-- Name: idx_dim_vehicles_codigo_voluntario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dim_vehicles_codigo_voluntario ON public.dim_vehicles USING btree (codigo_voluntario);


--
-- Name: idx_fact_invoices_codigo_associado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_invoices_codigo_associado ON public.fact_invoices USING btree (codigo_associado);


--
-- Name: idx_fact_invoices_codigo_regional; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_invoices_codigo_regional ON public.fact_invoices USING btree (codigo_regional);


--
-- Name: idx_fact_invoices_sk_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_invoices_sk_customer ON public.fact_invoices USING btree (sk_customer);


--
-- Name: uq_dim_customers_vigente; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_dim_customers_vigente ON public.dim_customers USING btree (codigo_associado) WHERE vigente;


--
-- Name: uq_dim_vehicles_vigente; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_dim_vehicles_vigente ON public.dim_vehicles USING btree (codigo_veiculo) WHERE vigente;


--
-- Name: fact_delinquency_snapshot fk_delinquency_sk_customer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_delinquency_snapshot
    ADD CONSTRAINT fk_delinquency_sk_customer FOREIGN KEY (sk_customer) REFERENCES public.dim_customers(sk_customer);


--
-- Name: dim_customers fk_dim_customers_codigo_cooperativa; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_customers
    ADD CONSTRAINT fk_dim_customers_codigo_cooperativa FOREIGN KEY (codigo_cooperativa) REFERENCES public.dim_cooperatives(codigo_cooperativa);


--
-- Name: dim_customers fk_dim_customers_codigo_regional; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_customers
    ADD CONSTRAINT fk_dim_customers_codigo_regional FOREIGN KEY (codigo_regional) REFERENCES public.dim_regionals(codigo_regional);


--
-- Name: dim_customers fk_dim_customers_codigo_voluntario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_customers
    ADD CONSTRAINT fk_dim_customers_codigo_voluntario FOREIGN KEY (codigo_voluntario) REFERENCES public.dim_volunteers(codigo_voluntario);


--
-- Name: dim_vehicles fk_dim_vehicles_codigo_cooperativa; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_vehicles
    ADD CONSTRAINT fk_dim_vehicles_codigo_cooperativa FOREIGN KEY (codigo_cooperativa) REFERENCES public.dim_cooperatives(codigo_cooperativa);


--
-- Name: dim_vehicles fk_dim_vehicles_codigo_regional; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_vehicles
    ADD CONSTRAINT fk_dim_vehicles_codigo_regional FOREIGN KEY (codigo_regional) REFERENCES public.dim_regionals(codigo_regional);


--
-- Name: dim_vehicles fk_dim_vehicles_codigo_voluntario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_vehicles
    ADD CONSTRAINT fk_dim_vehicles_codigo_voluntario FOREIGN KEY (codigo_voluntario) REFERENCES public.dim_volunteers(codigo_voluntario);


--
-- Name: fact_invoices fk_fact_invoices_codigo_regional; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_invoices
    ADD CONSTRAINT fk_fact_invoices_codigo_regional FOREIGN KEY (codigo_regional) REFERENCES public.dim_regionals(codigo_regional);


--
-- Name: fact_invoices fk_fact_invoices_sk_customer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_invoices
    ADD CONSTRAINT fk_fact_invoices_sk_customer FOREIGN KEY (sk_customer) REFERENCES public.dim_customers(sk_customer);


--
-- PostgreSQL database dump complete
--


