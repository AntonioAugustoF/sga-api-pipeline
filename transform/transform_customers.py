import os
import requests
import pandas as pd
from infra.loader import load_raw_to_dataframe
from infra.config import config
from infra.authenticator import authenticate_user

def get_status_lookup(user_token) -> dict:
    """Returns a dict mapping codigo_situacao -> descricao_situacao."""
    url = f"{config.API_BASE_URL}/listar/situacao/todos"
    headers = {"Authorization": f"Bearer {user_token}"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    return {str(s["codigo_situacao"]): s["descricao_situacao"] for s in data}


def transform() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = load_raw_to_dataframe("customers")

    df.columns = df.columns.str.lower().str.strip()
    df["codigo_situacao"] = df["codigo_situacao"].astype(str).str.strip()
    df = df.drop_duplicates(subset=["codigo_associado"])
    df["opcoes_notificacao"] = df["opcoes_notificacao"].astype(str)
    df["campos_opcionais"] = df["campos_opcionais"].astype(str)
    df = df.dropna(how="all")

    # Build history DataFrame
    user_token = authenticate_user()
    status_lookup = get_status_lookup(user_token)

    df_history = df[["codigo_associado", "codigo_situacao"]].copy()
    df_history["descricao_situacao"] = df_history["codigo_situacao"].map(status_lookup)
    df_history["data_extracao"] = pd.Timestamp.now().date()

    # Save to processed/
    current_date = pd.Timestamp.now().strftime("%Y-%m-%d")
    output_path = os.path.join("data", "processed", f"customers_{current_date}.parquet")
    df.to_parquet(output_path, index=False)

    print(f"✅ Customers transformed: {len(df)} rows")
    print(f"💾 File successfully saved to: {output_path}")
    return df, df_history


if __name__ == "__main__":
    df, df_history = transform()
    print(df.head())
    print(df.dtypes)
    print(df_history.head())