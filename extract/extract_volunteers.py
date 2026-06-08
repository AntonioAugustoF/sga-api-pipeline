import os
import json
import requests
from datetime import datetime
from infra.config import config
from infra.authenticator import authenticate_user
from infra.logger import get_logger

logger = get_logger(__name__)


def extract_volunteers_by_status(status_name, user_token):
    url = f"{config.API_BASE_URL}/listar/voluntario/{status_name}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    
    current_page = 0
    status_volunteers = []
    
    while True:
        payload = {
            "situacao": status_name,
            "pagina": current_page
        }
        
        response = requests.get(url, headers=headers, json=payload, timeout=30)  # ← GET
        response.raise_for_status()
        data = response.json()
        
        volunteers = data if isinstance(data, list) else data.get("voluntarios", [])
        if not volunteers:
            break
            
        for volunteer in volunteers:
            volunteer["situacao_origem"] = status_name
            
        status_volunteers.extend(volunteers)
        logger.info(f"Status '{status_name}' | Page {current_page}: {len(volunteers)} volunteers extracted.")
        
        if len(volunteers) < 5000:
            break
            
        current_page += 1
        
    return status_volunteers


def run_volunteer_extraction():
    logger.info("Starting volunteer extraction pipeline...")
    
    try:
        user_token = authenticate_user()
        
        target_statuses = ["ativo", "inativo"]
        all_records = []
        
        for status in target_statuses:
            try:
                records = extract_volunteers_by_status(status, user_token)
                all_records.extend(records)
            except Exception as e:
                logger.warning(f"Error extracting volunteers for status {status}: {e}")
                
        seen_volunteers = set()
        unique_volunteers = []
        
        for volunteer in all_records:
            volunteer_id = volunteer.get("codigo_voluntario")
            if volunteer_id not in seen_volunteers:
                seen_volunteers.add(volunteer_id)
                unique_volunteers.append(volunteer)
                
        logger.info(f"Total extracted: {len(all_records)} | Unique: {len(unique_volunteers)}")
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        file_name = f"volunteers_{current_date}.json"
        output_path = os.path.join("data", "raw", file_name)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_volunteers, f, ensure_ascii=False, indent=2)
            
        logger.info(f"File successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Critical failure in the volunteer extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_volunteer_extraction()