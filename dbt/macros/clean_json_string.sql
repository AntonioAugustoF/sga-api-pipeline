{% macro clean_json_string(key, source_column='payload') %}
    {#-
      Mirrors infra.transformations.cast_string_columns: strip, then lowercase,
      preserving nulls as nulls and empty strings as empty strings.
      
      btrim is given the explicit character set because Python's str.strip()
      removes every whitespace character, while btrim defaults to spaces only.
    -#}
    lower(btrim({{ source_column }} ->> '{{ key }}', E' \t\n\r\f\v'))
{% endmacro %}