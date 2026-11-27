-- Every invoice observed in this run's listing batches: the invoice windows,
-- plus the open invoices the windows did not bring.
--
-- The delinquency extraction is the full list of open invoices and has the same
-- payload shape as the invoice listing, but it used to feed only the snapshot.
-- An open invoice outside every window — issued long ago, due long ago — was
-- therefore in the snapshot and nowhere else: absent from fact_invoices, with
-- no rows in the bridge, and so attributed to no vehicle in the delinquency
-- marts. On 2026-11-27 that was 28 invoices; over the snapshot's history, 30
-- invoices and R$115k of open value.
--
-- The invoice listing wins when an invoice is in both: it is the batch the
-- fact has always been built from, and the two are minutes apart.

with invoices as (

    select * from {{ ref('stg_sga__invoices') }}

), delinquency as (

    select * from {{ ref('stg_sga__delinquency') }}

)

select * from invoices

union all

select d.*
from delinquency d
where not exists (select 1 from invoices i where i.codigo_boleto = d.codigo_boleto)
