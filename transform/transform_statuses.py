import os

import pandas as pd

from infra.loader import load_raw_to_dataframe
from infra.logger import get_logger
from infra.transformations import (
    cast_string_columns,
    remove_duplicates,
    remove_empty_rows,
    rename_columns,
)

logger = get_logger(__name__)

STATUS_STR_COLS = ["codigo_situacao", "descricao_situacao", "cor_linha", "cor_fonte"]

INVOICE_STATUS_RENAMES = {
    "codigo_situacaoboleto": "codigo_situacao_boleto",
    "descricao": "descricao_situacao_boleto",
}

INVOICE_STATUS_STR_COLS = ["codigo_situacao_boleto", "descricao_situacao_boleto"]


def _to_boolean(series: pd.Series, true_values: set[str]) -> pd.Series:
    """Maps the API's textual flags to real booleans, preserving nulls.

    Compared case-insensitively because cast_string_columns lowercases upstream
    and the API is not consistent between domains ("Y"/"N" vs "SIM"/"NÃO").
    """
    def convert(value) -> bool | None:
        if pd.isna(value):
            return None
        return str(value).strip().lower() in true_values

    return series.apply(convert).astype("boolean")


def transform_statuses() -> pd.DataFrame:
    """Transforms the registration status reference list (customers and vehicles)."""
    df = load_raw_to_dataframe("statuses")
    df = rename_columns(df)
    df = cast_string_columns(df, STATUS_STR_COLS)

    # "situacao" flags whether the status itself is still in use by the source
    # system, not whether the customer/vehicle carrying it is active.
    df["situacao_ativa"] = _to_boolean(df["situacao"], {"ativo"})
    df = df.drop(columns=["situacao"], errors="ignore")

    df = remove_duplicates(df, subset=["codigo_situacao"])
    df = remove_empty_rows(df)

    current_date = pd.Timestamp.now().strftime("%Y-%m-%d")
    output_path = os.path.join("data", "processed", f"statuses_{current_date}.parquet")
    df.to_parquet(output_path, index=False)

    logger.info(f"Statuses transformed: {len(df)} rows")
    logger.info(f"File successfully saved to: {output_path}")
    return df


def transform_invoice_statuses() -> pd.DataFrame:
    """Transforms the invoice status reference list.

    considerado_inadimplencia and pago encode business rules that currently live
    only in the source API — persisting them makes the delinquency views auditable
    and records when the source changes its mind about a status.
    """
    df = load_raw_to_dataframe("invoice_statuses")
    df = rename_columns(df)
    df = df.rename(columns=INVOICE_STATUS_RENAMES)
    df = cast_string_columns(df, INVOICE_STATUS_STR_COLS)

    df["considerado_inadimplencia"] = _to_boolean(df["considerado_inadimplencia"], {"y", "s", "sim"})
    df["pago"] = _to_boolean(df["pago"], {"sim", "s", "y"})

    df = remove_duplicates(df, subset=["codigo_situacao_boleto"])
    df = remove_empty_rows(df)

    current_date = pd.Timestamp.now().strftime("%Y-%m-%d")
    output_path = os.path.join("data", "processed", f"invoice_statuses_{current_date}.parquet")
    df.to_parquet(output_path, index=False)

    logger.info(f"Invoice statuses transformed: {len(df)} rows")
    logger.info(f"File successfully saved to: {output_path}")
    return df


if __name__ == "__main__":
    for frame in (transform_statuses(), transform_invoice_statuses()):
        logger.info(frame.head().to_string())
        logger.info(frame.dtypes.to_string())
