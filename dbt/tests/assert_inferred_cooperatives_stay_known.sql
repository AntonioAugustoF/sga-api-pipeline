-- Two cooperatives are known to be referenced but absent from the API. A third
-- means the source stopped returning something it used to, which is a coverage
-- change worth investigating rather than absorbing silently.
{{ config(error_if = '>2', warn_if = '>0') }}

select codigo_cooperativa
from {{ ref('int_cooperatives_inferred') }}
