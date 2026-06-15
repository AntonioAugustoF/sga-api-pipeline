import os
import pandas as pd
from infra.loader import load_raw_to_dataframe
from infra.logger import get_logger
from infra.transformations import (
    rename_columns,
    remove_duplicates,
    remove_empty_rows,
    cast_string_columns,
)

logger = get_logger(__name__)

STR_COLS = [
    "codigo_regional", "nome", "nome_fantasia", "cnpj", "logradouro",
    "numero", "complemento", "bairro", "cidade", "estado", "cep",
    "email", "telefone", "situacao"
]

COLS_TO_DROP = ["website", "situacao_origem"]


def transform() -> pd.DataFrame:
    df = load_raw_to_dataframe("regionals")
    df = rename_columns(df)
    df = cast_string_columns(df, STR_COLS)
    df = remove_duplicates(df, subset=["codigo_regional"])
    df = remove_empty_rows(df)


    current_date = pd.Timestamp.now().strftime("%Y-%m-%d")
    output_path = os.path.join("data", "processed", f"regionals_{current_date}.parquet")
    df.to_parquet(output_path, index=False)

    logger.info(f"Regionals transformed: {len(df)} rows")
    logger.info(f"File successfully saved to: {output_path}")
    return df

if __name__ == "__main__":
    df = transform()
    logger.info(df.head().to_string())
    logger.info(df.dtypes.to_string())