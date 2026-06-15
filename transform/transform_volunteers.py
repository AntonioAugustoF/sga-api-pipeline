import os
import pandas as pd
from infra.loader import load_raw_to_dataframe
from infra.logger import get_logger
from infra.transformations import (
    rename_columns,
    remove_duplicates,
    remove_empty_rows,
    cast_string_columns,
    cast_date_columns,
)

logger = get_logger(__name__)

STR_COLS = [
    "codigo_voluntario", "nome", "cpf", "cep", "telefone", "telefone_comercial",
    "celular", "email", "situacao", "codigo_classificacao", "logradouro", "numero", "complemento", "bairro",
    "cidade", "estado", "situacao_origem", "cooperativas"
]

DATE_COLS = ["data_cadastro", "data_nascimento"]

COLS_TO_DROP = [
    "formato_pagamento", "formato_pagamento_residual",
    "valor_pagamento", "valor_pagamento_residual", "obs"
]


def transform() -> pd.DataFrame:
    df = load_raw_to_dataframe("volunteers")
    df = rename_columns(df)
    df = df.drop(columns=COLS_TO_DROP, errors="ignore")
    df = cast_string_columns(df, STR_COLS)
    df = cast_date_columns(df, DATE_COLS)
    df = remove_duplicates(df, subset=["codigo_voluntario"])
    df = remove_empty_rows(df)

    current_date = pd.Timestamp.now().strftime("%Y-%m-%d")
    output_path = os.path.join("data", "processed", f"volunteers_{current_date}.parquet")
    df.to_parquet(output_path, index=False)

    logger.info(f"Volunteers transformed: {len(df)} rows")
    logger.info(f"File successfully saved to: {output_path}")
    return df


if __name__ == "__main__":
    df = transform()
    logger.info(df.head().to_string())
    logger.info(df.dtypes.to_string())