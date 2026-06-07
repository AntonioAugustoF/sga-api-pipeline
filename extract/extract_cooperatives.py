import os
import json
import requests
from datetime import datetime
from infra.config import config
from infra.authenticator import authenticate_user

def extract_cooperatives_by_status(status_name, user_token):
    url = f"{config.API_BASE_URL}/listar/cooperativa/ativo"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    
    current_page = 0
    status_cooperatives = []
    
    while True:
        payload = {
            "situacao": status_name,
            "pagina": current_page
        }
        
        response = requests.get(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        cooperatives = data if isinstance(data, list) else data.get("cooperativas", [])
        if not cooperatives:
            break
            
        for cooperative in cooperatives:
            cooperative["situacao_origem"] = status_name
            
        status_cooperatives.extend(cooperatives)
        print(f"Status '{status_name}' | Page {current_page}: {len(cooperatives)} cooperatives extracted.")
        
        if len(cooperatives) < 5000:
            break
            
        current_page += 1
        
    return status_cooperatives


def run_cooperative_extraction():
    print(f"⏳ [{datetime.now()}] Starting cooperative extraction pipeline...")
    
    try:
        user_token = authenticate_user()
        
        target_statuses = ["ativo", "inativo"]
        all_records = []
        
        for status in target_statuses:
            try:
                records = extract_cooperatives_by_status(status, user_token)
                all_records.extend(records)
            except Exception as e:
                print(f"⚠️ Error extracting cooperatives for status {status}: {e}")
                
        seen_cooperatives = set()
        unique_cooperatives = []
        
        for cooperative in all_records:
            cooperative_id = cooperative.get("codigo_cooperativa")
            if cooperative_id not in seen_cooperatives:
                seen_cooperatives.add(cooperative_id)
                unique_cooperatives.append(cooperative)
                
        print(f"\n📊 Total extracted: {len(all_records)} | Unique: {len(unique_cooperatives)}")
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        file_name = f"cooperatives_{current_date}.json"
        output_path = os.path.join("data", "raw", file_name)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_cooperatives, f, ensure_ascii=False, indent=2)
            
        print(f"💾 File successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        print(f"🚨 Critical failure in the cooperative extraction pipeline: {e}")
        return None


if __name__ == "__main__":
    run_cooperative_extraction()