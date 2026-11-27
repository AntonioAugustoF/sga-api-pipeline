-- An invoice the warehouse holds as open (status 2) must be in today's
-- delinquency extraction, which is the full list of open invoices.
--
-- Before extract/extract_invoice_lookups.py existed nothing checked this, and
-- 1,082 invoices cancelled outside the extraction windows sat in the fact as
-- 'aberto'. The lookup re-reads every such invoice each night, so what is left
-- here is the backlog still being drained (the lookup re-reads at most 150 per
-- night, because the API blocks bursts), an invoice the source no longer has
-- at all (logged by the lookup), or a status change between the invoice and
-- delinquency extractions of the same run.
--
-- The error threshold sits above the 1,082 found on 2026-11-27, so draining
-- that backlog warns instead of failing the nightly build. Lower it once the
-- warning has gone quiet: a count growing past it means the reconciliation
-- itself stopped working.
{{ config(warn_if = '>0', error_if = '>1500') }}

with open_today as (

    select codigo_boleto from {{ ref('stg_sga__delinquency') }}

), facts as (

    select codigo_boleto, codigo_situacao_boleto from {{ ref('fact_invoices_base') }}

)

select f.codigo_boleto
from facts f
where f.codigo_situacao_boleto = '2'
  and not exists (select 1 from open_today o where o.codigo_boleto = f.codigo_boleto)
