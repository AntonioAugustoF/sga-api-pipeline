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
    cast_numeric_columns,
)

logger = get_logger(__name__)

STR_COLS = [
    "codigo_boleto", "nosso_numero", "mes_referente", "pago",
    "codigo_associado", "cpf_associado", "codigo_situacao_associado",
    "descricao_situacao_associado", "codigo_regional_associado", "nome_regional_associado",
    "codigo_situacao_boleto", "descricao_situacao_boleto", "codigo_regional",
    "nome_regional_boleto", "referente", "codigo_mgfformapagamento",
    "codigo_forma_pagamento", "descricao_forma_pagamento",
    "descricao_tipo_cobranca_recorrente", "codigo_tipo_boleto", "descricao_tipo_boleto",
    "codigo_conta", "codigo_banco", "nome_banco", "agencia", "conta",
    "descricao_tipo_baixa_boleto", "veiculo", "beneficiario", "codigo_situacao",
]

DATE_COLS = [
    "data_emissao", "data_vencimento_original", "data_vencimento",
    "data_pagamento", "data_credito_banco",
]

NUMERIC_COLS = [
    "valor_boleto", "valor_pagamento", "tarifa_cobranca_banco",
    "parcela_paga", "qtde_parcela",
]


def transform() -> pd.DataFrame:
    df = load_raw_to_dataframe("invoices")
    df = rename_columns(df)
    df = cast_string_columns(df, STR_COLS)
    df = cast_date_columns(df, DATE_COLS)
    df = cast_numeric_columns(df, NUMERIC_COLS)
    df = remove_duplicates(df, subset=["codigo_boleto"])
    df = remove_empty_rows(df)

    current_date = pd.Timestamp.now().strftime("%Y-%m-%d")
    output_path = os.path.join("data", "processed", f"invoices_{current_date}.parquet")
    df.to_parquet(output_path, index=False)

    logger.info(f"Invoices transformed: {len(df)} rows")
    logger.info(f"File successfully saved to: {output_path}")
    return df


if __name__ == "__main__":
    df = transform()
    logger.info(df.head().to_string())
    logger.info(df.dtypes.to_string())
