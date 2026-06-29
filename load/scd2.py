import pandas as pd
from sqlalchemy import text, inspect
from infra.db_connector import get_db_engine
from infra.logger import get_logger
from load.load_facts import sync_table_schema

logger = get_logger(__name__)


def upsert_scd2_dimension(
    df: pd.DataFrame,
    table_name: str,
    natural_key: str,
    monitored_columns: list[str],
    reference_date,
) -> None:
    """Upserts a dimension with SCD Type 2 semantics on `monitored_columns`.

    - New natural keys are inserted as a new current version.
    - Existing natural keys with a change in any monitored column close out
      the current version (vigente=False, valido_ate=reference_date) and open
      a new current version (vigente=True, valido_de=reference_date).
    - Existing natural keys with no monitored change have their non-monitored
      attributes refreshed in place, without opening a new version.
    - Natural keys absent from `df` are left untouched: extraction can be
      partial, so absence is never treated as a business change.
    - Reruns for the same reference_date update that day's version in place
      instead of duplicating it.
    """
    engine = get_db_engine()
    attr_columns = [c for c in df.columns if c != natural_key]
    all_columns = [natural_key] + attr_columns
    non_monitored = [c for c in attr_columns if c not in monitored_columns]
    temp_table = f"_temp_{table_name}"

    target_cols_sql = ", ".join(f'"{c}"' for c in all_columns)
    select_cols_sql = ", ".join(f't."{c}"' for c in all_columns)

    with engine.begin() as conn:
        if not inspect(engine).has_table(table_name):
            logger.info(f"Table '{table_name}' not found. Creating SCD2 structure...")
            scd_df = df.copy()
            scd_df["valido_de"] = reference_date
            scd_df["valido_ate"] = None
            scd_df["vigente"] = True
            scd_df.to_sql(table_name, conn, if_exists="replace", index=False, chunksize=1000)
            conn.execute(text(
                f'ALTER TABLE {table_name} ADD CONSTRAINT uq_{table_name}_nk_validade '
                f'UNIQUE ("{natural_key}", valido_de)'
            ))
            conn.execute(text(
                f'CREATE UNIQUE INDEX uq_{table_name}_vigente ON {table_name} ("{natural_key}") '
                f'WHERE vigente'
            ))
            logger.info(f"Table '{table_name}' created with {len(scd_df)} current-version rows.")
            return

        sync_table_schema(conn, engine, table_name, df)
        df.to_sql(temp_table, conn, if_exists="replace", index=False, chunksize=1000)

        monitored_diff = " OR ".join(f's."{c}" IS DISTINCT FROM c."{c}"' for c in monitored_columns)

        changed_cte = f"""
            SELECT s."{natural_key}" AS nk
            FROM "{temp_table}" s
            JOIN {table_name} c ON c."{natural_key}" = s."{natural_key}" AND c.vigente
            WHERE {monitored_diff}
        """
        new_keys_cte = f"""
            SELECT s."{natural_key}" AS nk
            FROM "{temp_table}" s
            LEFT JOIN {table_name} c ON c."{natural_key}" = s."{natural_key}"
            WHERE c."{natural_key}" IS NULL
        """

        closed = conn.execute(text(f"""
            UPDATE {table_name}
            SET vigente = false, valido_ate = :ref_date
            WHERE vigente AND "{natural_key}" IN ({changed_cte})
        """), {"ref_date": reference_date})
        logger.info(f"Closed {closed.rowcount} outdated version(s) in '{table_name}'.")

        update_set = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in attr_columns)
        inserted = conn.execute(text(f"""
            INSERT INTO {table_name} ({target_cols_sql}, valido_de, valido_ate, vigente)
            SELECT {select_cols_sql}, :ref_date, NULL, true
            FROM "{temp_table}" t
            WHERE t."{natural_key}" IN ({changed_cte} UNION {new_keys_cte})
            ON CONFLICT ("{natural_key}", valido_de) DO UPDATE SET
                {update_set}, vigente = true, valido_ate = NULL
        """), {"ref_date": reference_date})
        logger.info(f"Inserted/refreshed {inserted.rowcount} new version(s) into '{table_name}'.")

        if non_monitored:
            set_clause = ", ".join(f'"{c}" = t."{c}"' for c in non_monitored)
            refreshed = conn.execute(text(f"""
                UPDATE {table_name} d
                SET {set_clause}
                FROM "{temp_table}" t
                WHERE d."{natural_key}" = t."{natural_key}"
                  AND d.vigente
                  AND d."{natural_key}" NOT IN ({changed_cte})
            """))
            logger.info(f"Refreshed non-monitored attributes on {refreshed.rowcount} unchanged row(s).")

        conn.execute(text(f'DROP TABLE IF EXISTS "{temp_table}"'))
