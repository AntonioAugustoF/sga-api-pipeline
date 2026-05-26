import os
import json
import requests
from datetime import datetime
from infra.config import config
from infra.authenticator import authenticate_user


def extract_vehicles_by_status(status_code, user_token):
    """Extracts all vehicles for a specific status using pagination."""
    url = f"{config.API_BASE_URL}/listar/veiculo"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    
    payload = {
        "codigo_situacao": str(status_code),
        "quantidade_por_pagina": 1000,
        "inicio_paginacao": 0
    }
    
    status_vehicles = []
    total_vehicles = None
    
    while True:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if total_vehicles is None:
            total_vehicles = data.get("total_veiculos", 0)
            
        vehicles = data.get("veiculos", [])
        if not vehicles:
            break
            
        for vehicle in vehicles:
            # Enriches the raw data with the status code context
            vehicle["codigo_situacao"] = status_code
            
        status_vehicles.extend(vehicles)
        payload["inicio_paginacao"] += 1000
        
        if len(vehicles) < 1000 or len(status_vehicles) >= total_vehicles:
            break
            
    print(f"Status {status_code}: {len(status_vehicles)} vehicles extracted.")
    return status_vehicles


def run_vehicle_extraction():
    """Main function to orchestrate the full vehicle extraction process."""
    print(f"⏳ [{datetime.now()}] Starting vehicle extraction pipeline...")
    
    try:
        # 1. Authenticate to get the user token
        user_token = authenticate_user()
        
        # 2. Fetch all dynamic statuses
        url_statuses = f"{config.API_BASE_URL}/listar/situacao/todos"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {user_token}"
        }
        
        response = requests.get(url_statuses, headers=headers, timeout=30)
        response.raise_for_status()
        statuses_data = response.json()
        
        status_list = [s["codigo_situacao"] for s in statuses_data]
        print(f"📌 Statuses found to extract: {status_list}")
        
        # 3. Loop through statuses to gather all records
        all_records = []
        for status in status_list:
            try:
                records = extract_vehicles_by_status(status, user_token)
                all_records.extend(records)
            except Exception as e:
                print(f"⚠️ Error extracting status {status}: {e}")
                
        # 4. Remove duplicates based on 'codigo_veiculo'
        seen_vehicles = set()
        unique_vehicles = []
        
        for vehicle in all_records:
            vehicle_id = vehicle.get("codigo_veiculo")
            if vehicle_id not in seen_vehicles:
                seen_vehicles.add(vehicle_id)
                unique_vehicles.append(vehicle)
                
        print(f"\n📊 Total extracted: {len(all_records)} | Unique: {len(unique_vehicles)}")
        
        # 5. Save the raw file to the data/ folder (Staging area)
        current_date = datetime.now().strftime("%Y-%m-%d")
        file_name = f"raw_vehicles_{current_date}.json"
        output_path = os.path.join("data", file_name)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_vehicles, f, ensure_ascii=False, indent=2)
            
        print(f"💾 File successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        print(f"🚨 Critical failure in the extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_vehicle_extraction()