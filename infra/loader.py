import json
import os
from datetime import datetime
import pandas as pd
from infra.logger import get_logger

logger = get_logger(__name__)


def load_raw_to_dataframe(entity: str) -> pd.DataFrame:
    """Loads the most recent raw JSON file for a given entity into a DataFrame."""
    current_date = datetime.now().strftime("%Y-%m-%d")
    file_name = f"{entity}_{current_date}.json"
    file_path = os.path.join("data", "raw", file_name)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    logger.info(f"{file_name} loaded: {len(df)} rows | {len(df.columns)} columns")
    return df


def load_status_lookup(entity: str) -> dict:
    """Loads the most recent status lookup JSON file ({codigo_situacao: descricao_situacao}) for a given entity."""
    current_date = datetime.now().strftime("%Y-%m-%d")
    file_name = f"{entity}_status_lookup_{current_date}.json"
    file_path = os.path.join("data", "raw", file_name)

    with open(file_path, "r", encoding="utf-8") as f:
        lookup = json.load(f)

    logger.info(f"{file_name} loaded: {len(lookup)} statuses")
    return lookup