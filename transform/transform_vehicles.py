import os
import requests
import pandas as pd
from infra.loader import load_raw_to_dataframe
from infra.config import config
from infra.authenticator import authenticate_user
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
    "codigo_veiculo", "placa", "chassi", "renavam", "codigo_associado",
    "codigo_usuario", "codigo_tipo", "codigo_classificacao", "codigo_cota",
    "codigo_fipe", "valor_fipe_protegido", "codigo_depreciacao",
    "codigo_regional", "codigo_cooperativa",
    "codigo_marca", "codigo_modelo", "codigo_combustivel", "codigo_cor",
    "codigo_grupo_produto", "codigo_vencimento",
    "boleto_fisico", "mes_referente", "codigo_categoria", "tipo", "categoria",
    "marca", "modelo", "nome_associado", "rg_associado", "cpf_associado",
    "telefone", "ddd", "telefone_celular", "ddd_celular",
    "email", "codigo_situacao", "descricao_situacao", "codigo_voluntario",
    "nome_voluntario", "cpf_voluntario", "campos_opcionais"
]

DATE_COLS = [
    "data_reativacao", "data_alteracao", "data_cadastro",
    "data_contrato"
]

COLS_TO_DROP = [
    "hora_cadastro", "usuario_cadastro", "telefone_celular_aux",
    "ddd_celular_aux", "ddd_comercial", "telefone_comercial",  "data_contrato_final",
    "codigo_tabela_avaliacao", "codigo_tipo_adesao"
]


def get_status_lookup(user_token) -> dict:
    url = f"{config.API_BASE_URL}/listar/situacao/todos"
    headers = {"Authorization": f"Bearer {user_token}"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    return {str(s["codigo_situacao"]): s["descricao_situacao"] for s in data}


def transform() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = load_raw_to_dataframe("vehicles")
    df = rename_columns(df)
    df = df.drop(columns=COLS_TO_DROP, errors="ignore")
    df = cast_string_columns(df, STR_COLS)
    df = cast_date_columns(df, DATE_COLS)
    df = cast_numeric_columns(df, ["valor_fipe", "valor_fixo", "valor_adesao"], dtype="float")
    df = cast_numeric_columns(df, ["pontos", "ano_fabricacao", "ano_modelo", "mes_final_carne"], dtype="int")
    df = remove_duplicates(df, subset=["codigo_veiculo"])
    df = remove_empty_rows(df)

    user_token = authenticate_user()
    status_lookup = get_status_lookup(user_token)

    df_history = df[["codigo_veiculo", "codigo_situacao"]].copy()
    df_history["descricao_situacao"] = df_history["codigo_situacao"].map(status_lookup)
    df_history["data_extracao"] = pd.Timestamp.now().date()

    current_date = pd.Timestamp.now().strftime("%Y-%m-%d")
    output_path = os.path.join("data", "processed", f"vehicles_{current_date}.parquet")
    df.to_parquet(output_path, index=False)

    logger.info(f"Vehicles transformed: {len(df)} rows")
    logger.info(f"File successfully saved to: {output_path}")
    return df, df_history


if __name__ == "__main__":
    df, df_history = transform()
    logger.info(df.head().to_string())
    logger.info(df.dtypes.to_string())
    logger.info(df_history.head().to_string())