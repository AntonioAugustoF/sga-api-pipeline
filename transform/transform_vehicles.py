import os
import pandas as pd
from infra.loader import load_raw_to_dataframe

def transform() -> pd.DataFrame:
    df = load_raw_to_dataframe("vehicles")

    df.columns = df.columns.str.lower().str.strip()
    df["codigo_situacao"] = df["codigo_situacao"].astype(str).str.strip()
    df = df.drop_duplicates(subset=["codigo_veiculo"])
    df = df.dropna(how="all")

    # Save to processed/
    current_date = pd.Timestamp.now().strftime("%Y-%m-%d")
    output_path = os.path.join("data", "processed", f"vehicles_{current_date}.parquet")
    df.to_parquet(output_path, index=False)

    print(f"✅ Vehicles transformed: {len(df)} rows")
    print(f"💾 File successfully saved to: {output_path}")
    return df

if __name__ == "__main__":
    df = transform()
    print(df.head())
    print(df.dtypes)