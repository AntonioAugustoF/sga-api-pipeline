-- Source data carries typed-in dates that are impossible: birth years such as
-- 2972, 7973 and 9975, and birth dates in the future that produce a negative
-- age. Thirty customers are affected today.
--
-- The pandas path made these invisible rather than fixing them. pandas'
-- datetime64[ns] only spans 1677 to 2262, so to_datetime(errors="coerce")
-- silently returned NaT and the warehouse stored NULL. Postgres accepts the
-- values, so this model keeps what the source actually said and reports it here
-- instead. A wrong value that is visible can be corrected at the source; a
-- value quietly turned into NULL cannot.
--
-- The thresholds hold the line at what is known: these do not fail the build,
-- but a thirty-first case does.
{{ config(error_if = '>30', warn_if = '>0') }}

select
    codigo_associado,
    data_nascimento,
    data_vencimento_habilitacao,
    case
        when data_nascimento < date '1900-01-01' then 'nascimento anterior a 1900'
        when data_nascimento > current_date      then 'nascimento no futuro'
        else 'habilitacao vence daqui a mais de 20 anos'
    end as motivo
from {{ ref('stg_sga__customers') }}
where data_nascimento < date '1900-01-01'
   or data_nascimento > current_date
   or data_vencimento_habilitacao > current_date + interval '20 years'
