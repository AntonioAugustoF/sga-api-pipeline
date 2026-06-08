import os
import json
import requests
from datetime import datetime
from infra.config import config
from infra.authenticator import authenticate_user
from infra.logger import get_logger

logger = get_logger(__name__)


def extract_vehicles_by_status(status_code, user_token):
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
            vehicle["codigo_situacao"] = status_code
            
        status_vehicles.extend(vehicles)
        payload["inicio_paginacao"] += 1000
        
        if len(vehicles) < 1000 or len(status_vehicles) >= total_vehicles:
            break
            
    logger.info(f"Status {status_code}: {len(status_vehicles)} vehicles extracted.")
    return status_vehicles


def run_vehicle_extraction():
    logger.info("Starting vehicle extraction pipeline...")
    
    try:
        user_token = authenticate_user()
        
        url_statuses = f"{config.API_BASE_URL}/listar/situacao/todos"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {user_token}"
        }
        
        response = requests.get(url_statuses, headers=headers, timeout=30)
        response.raise_for_status()
        statuses_data = response.json()
        
        status_list = [s["codigo_situacao"] for s in statuses_data]
        logger.info(f"Statuses found to extract: {status_list}")
        
        all_records = []
        for status in status_list:
            try:
                records = extract_vehicles_by_status(status, user_token)
                all_records.extend(records)
            except Exception as e:
                logger.warning(f"Error extracting status {status}: {e}")
                
        seen_vehicles = set()
        unique_vehicles = []
        
        for vehicle in all_records:
            vehicle_id = vehicle.get("codigo_veiculo")
            if vehicle_id not in seen_vehicles:
                seen_vehicles.add(vehicle_id)
                unique_vehicles.append(vehicle)
                
        logger.info(f"Total extracted: {len(all_records)} | Unique: {len(unique_vehicles)}")
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        file_name = f"vehicles_{current_date}.json"
        output_path = os.path.join("data", "raw", file_name)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_vehicles, f, ensure_ascii=False, indent=2)
            
        logger.info(f"File successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Critical failure in the vehicle extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_vehicle_extraction()