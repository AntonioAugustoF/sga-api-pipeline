{% macro try_json_cast(key, type, source_column='payload') %}
    {#-
      Mirrors pandas' to_numeric(errors="coerce"): an unparseable value becomes
      null instead of aborting the model.
      
      pg_input_is_valid requires PostgreSQL 16 or newer. It is the one
      dialect-specific construct in the staging layer — BigQuery spells this
      SAFE_CAST — so it is isolated in a macro for optional phase B.
    -#}
    case
        when pg_input_is_valid({{ source_column }} ->> '{{ key }}', '{{ type }}')
        then ({{ source_column }} ->> '{{ key }}')::{{ type }}
    end
{% endmacro %}