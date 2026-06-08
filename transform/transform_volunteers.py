import os
import pandas as pd
from infra.loader import load_raw_to_dataframe
from infra.logger import get_logger

logger = get_logger(__name__)


def transform() -> pd.DataFrame:
    df = load_raw_to_dataframe("volunteers")

    df.columns = df.columns.str.lower().str.strip()
    df["situacao_origem"] = df["situacao_origem"].str.lower().str.strip()
    df = df.drop_duplicates(subset=["codigo_voluntario"])
    df["cooperativas"] = df["cooperativas"].astype(str)
    df = df.dropna(how="all")

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