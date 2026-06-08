import os
import requests
import pandas as pd
from infra.loader import load_raw_to_dataframe
from infra.config import config
from infra.authenticator import authenticate_user
from infra.logger import get_logger

logger = get_logger(__name__)


def get_status_lookup(user_token) -> dict:
    url = f"{config.API_BASE_URL}/listar/situacao/todos"
    headers = {"Authorization": f"Bearer {user_token}"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    return {str(s["codigo_situacao"]): s["descricao_situacao"] for s in data}


def transform() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = load_raw_to_dataframe("vehicles")

    df.columns = df.columns.str.lower().str.strip()
    df["codigo_situacao"] = df["codigo_situacao"].astype(str).str.strip()
    df = df.drop_duplicates(subset=["codigo_veiculo"])
    df["campos_opcionais"] = df["campos_opcionais"].astype(str)
    df = df.dropna(how="all")

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