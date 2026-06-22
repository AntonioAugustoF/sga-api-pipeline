import os
import pandas as pd
from infra.loader import load_raw_to_dataframe, load_status_lookup
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
    "codigo_associado", "codigo_situacao", "nome", "sexo", "tipo_pessoa",
    "rg_associado", "cnh", "categoria_cnh",
    "dia_vencimento", "cpf", "ddd", "telefone", "codigo_profissao",
    "codigo_classificacao", "ddd_celular", "telefone_celular", "email",
    "cep", "logradouro", "numero", "complemento", "bairro",
    "cidade", "estado", "codigo_regional", "codigo_cooperativa",
    "codigo_voluntario"
]

DATE_COLS = [
    "data_nascimento", "data_vencimento_habilitacao",
    "data_cadastro_associado", "data_contrato_associado"
]

COLS_TO_DROP = ["radio", "radio2", "hora_contrato_associado", "orgao_expedidor_rg",
    "data_expedicao_rg", "email_auxiliar", "pontos", "opcoes_notificacao", "campos_opcionais",
    "ddd_celular_aux", "telefone_celular_aux", "ddd_comercial", "telefone_comercial",
]


def transform() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = load_raw_to_dataframe("customers")
    df = rename_columns(df)
    df = df.drop(columns=COLS_TO_DROP, errors="ignore")
    df = cast_string_columns(df, STR_COLS)
    df = cast_date_columns(df, DATE_COLS)
    df = remove_duplicates(df, subset=["codigo_associado"])
    df = remove_empty_rows(df)

    status_lookup = load_status_lookup("customers")

    df_history = df[["codigo_associado", "codigo_situacao"]].copy()
    df_history["descricao_situacao"] = df_history["codigo_situacao"].map(status_lookup)
    df_history["data_extracao"] = pd.Timestamp.now().date()

    current_date = pd.Timestamp.now().strftime("%Y-%m-%d")
    output_path = os.path.join("data", "processed", f"customers_{current_date}.parquet")
    df.to_parquet(output_path, index=False)

    history_dir = os.path.join("data", "processed", "history")
    os.makedirs(history_dir, exist_ok=True)
    df_history.to_parquet(os.path.join(history_dir, f"customers_{current_date}.parquet"), index=False)

    logger.info(f"Customers transformed: {len(df)} rows")
    logger.info(f"File successfully saved to: {output_path}")
    return df, df_history


if __name__ == "__main__":
    df, df_history = transform()
    logger.info(df.head().to_string())
    logger.info(df.dtypes.to_string())
    logger.info(df_history.head().to_string())