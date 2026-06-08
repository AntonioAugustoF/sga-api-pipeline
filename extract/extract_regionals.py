import os
import json
import requests
from datetime import datetime
from infra.config import config
from infra.authenticator import authenticate_user
from infra.logger import get_logger

logger = get_logger(__name__)


def extract_regionals_by_status(status_name, user_token):
    url = f"{config.API_BASE_URL}/listar/regional/ativo"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    
    current_page = 0
    status_regionals = []
    
    while True:
        payload = {
            "situacao": status_name,
            "pagina": current_page
        }
        
        response = requests.get(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        regionals = data if isinstance(data, list) else data.get("regionais", [])
        if not regionals:
            break
            
        for regional in regionals:
            regional["situacao_origem"] = status_name
            
        status_regionals.extend(regionals)
        logger.info(f"Status '{status_name}' | Page {current_page}: {len(regionals)} regionals extracted.")
        
        if len(regionals) < 5000:
            break
            
        current_page += 1
        
    return status_regionals


def run_regional_extraction():
    logger.info("Starting regional extraction pipeline...")
    
    try:
        user_token = authenticate_user()
        
        target_statuses = ["ativo", "inativo"]
        all_records = []
        
        for status in target_statuses:
            try:
                records = extract_regionals_by_status(status, user_token)
                all_records.extend(records)
            except Exception as e:
                logger.warning(f"Error extracting regionals for status {status}: {e}")
                
        seen_regionals = set()
        unique_regionals = []
        
        for regional in all_records:
            regional_id = regional.get("codigo_regional")
            if regional_id not in seen_regionals:
                seen_regionals.add(regional_id)
                unique_regionals.append(regional)
                
        logger.info(f"Total extracted: {len(all_records)} | Unique: {len(unique_regionals)}")
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        file_name = f"regionals_{current_date}.json"
        output_path = os.path.join("data", "raw", file_name)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_regionals, f, ensure_ascii=False, indent=2)
            
        logger.info(f"File successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Critical failure in the regional extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_regional_extraction()