{% macro clean_json_string(key, source_column='payload') %}
    {#-
      Mirrors infra.transformations.cast_string_columns: strip, then lowercase,
      preserving nulls as nulls and empty strings as empty strings.

      The trim set is explicit and includes U+00A0. Python's str.strip() removes
      every Unicode whitespace character, while btrim removes only what it is
      given — and the source turned out to carry non-breaking spaces in 245
      invoice descriptions, which read as a one-character difference that no
      amount of staring at the text would reveal.
    -#}
    lower(btrim({{ source_column }} ->> '{{ key }}', E' \t\n\r\f\v' || U&'\00A0'))
{% endmacro %}
