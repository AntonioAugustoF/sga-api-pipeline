import os
import pandas as pd
from infra.loader import load_raw_to_dataframe
from infra.logger import get_logger
from infra.transformations import (
    rename_columns,
    remove_duplicates,
    remove_empty_rows,
    cast_string_columns,
    cast_numeric_columns,
)

logger = get_logger(__name__)

STR_COLS = [
    "codigo_cooperativa", "nome", "logradouro", "numero", "complemento",
    "bairro", "cidade", "estado", "cep", "email", "cpf", "telefone", "situacao"
]

COLS_TO_DROP = [
    "formato_pagamento", "formato_pagamento_residual",
    "valor_pagamento", "valor_pagamento_residual", "telefone_comercial",
    "contato", "situacao_origem"
]

def transform() -> pd.DataFrame:
    df = load_raw_to_dataframe("cooperatives")
    df = rename_columns(df)
    df = cast_string_columns(df, STR_COLS)
    df = cast_numeric_columns(df, ["valor_pagamento", "valor_pagamento_residual"], dtype="float")
    df = remove_duplicates(df, subset=["codigo_cooperativa"])
    df = remove_empty_rows(df)

    current_date = pd.Timestamp.now().strftime("%Y-%m-%d")
    output_path = os.path.join("data", "processed", f"cooperatives_{current_date}.parquet")
    df.to_parquet(output_path, index=False)

    logger.info(f"Cooperatives transformed: {len(df)} rows")
    logger.info(f"File successfully saved to: {output_path}")
    return df


if __name__ == "__main__":
    df = transform()
    logger.info(df.head().to_string())
    logger.info(df.dtypes.to_string())