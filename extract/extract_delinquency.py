import os
import json
from datetime import datetime
from infra.config import config
from infra.authenticator import authenticate_user
from extract.extract_invoices import _fetch_by_status
from infra.logger import get_logger

logger = get_logger(__name__)

DELINQUENCY_STATUS = 2


def run_delinquency_extraction():
    logger.info("Starting delinquency extraction (status=2, no date filter)...")

    try:
        user_token = authenticate_user()
        records = _fetch_by_status(DELINQUENCY_STATUS, user_token, date_filters={})

        logger.info(f"Total open invoices extracted: {len(records)}")

        current_date = datetime.now().strftime("%Y-%m-%d")
        output_path = os.path.join("data", "raw", f"delinquency_{current_date}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        logger.info(f"File successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Critical failure in delinquency extraction: {e}")
        raise


if __name__ == "__main__":
    run_delinquency_extraction()
