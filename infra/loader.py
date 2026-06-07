import json
import pandas as pd

def load_raw_to_dataframe(entity: str) -> pd.DataFrame:
    """Loads the most recent raw JSON file for a given entity into a DataFrame."""
    import os
    from datetime import datetime

    current_date = datetime.now().strftime("%Y-%m-%d")
    file_name = f"{entity}_{current_date}.json"
    file_path = os.path.join("data", "raw", file_name)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    print(f"✅ '{file_name}' loaded: {len(df)} rows | {len(df.columns)} columns")
    return df