import os
import json
import requests
from datetime import datetime
from infra.config import config
from infra.authenticator import authenticate_user
from infra.logger import get_logger

logger = get_logger(__name__)


def extract_customers_by_status(status_code, user_token):
    url = f"{config.API_BASE_URL}/listar/associado"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    
    payload = {
        "codigo_situacao": str(status_code),
        "quantidade_por_pagina": 1000,
        "inicio_paginacao": 0
    }
    
    status_customers = []
    total_customers = None
    
    while True:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        if total_customers is None:
            total_customers = data.get("total_associados", 0)
            
        customers = data.get("associados", [])
        if not customers:
            break
            
        for customer in customers:
            customer["codigo_situacao"] = status_code
            
        status_customers.extend(customers)
        payload["inicio_paginacao"] += 1000
        
        if len(customers) < 1000 or len(status_customers) >= total_customers:
            break
            
    logger.info(f"Status {status_code}: {len(status_customers)} customers extracted.")
    return status_customers


def run_customer_extraction():
    logger.info("Starting customer extraction pipeline...")
    
    try:
        user_token = authenticate_user()
        
        url_statuses = f"{config.API_BASE_URL}/listar/situacao/todos"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {user_token}"
        }
        
        response = requests.get(url_statuses, headers=headers, timeout=60)
        response.raise_for_status()
        statuses_data = response.json()
        
        status_list = [s["codigo_situacao"] for s in statuses_data]
        logger.info(f"Statuses found to extract: {status_list}")
        
        all_records = []
        for status in status_list:
            try:
                records = extract_customers_by_status(status, user_token)
                all_records.extend(records)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 406:
                    logger.info(f"Status {status} not supported by /associado (406) — skipping.")
                else:
                    logger.warning(f"HTTP error extracting status {status}: {e}")
            except Exception as e:
                logger.warning(f"Error extracting status {status}: {e}")
                
        seen_customers = set()
        unique_customers = []
        
        for customer in all_records:
            customer_id = customer.get("codigo_associado")
            if customer_id not in seen_customers:
                seen_customers.add(customer_id)
                unique_customers.append(customer)
                
        logger.info(f"Total extracted: {len(all_records)} | Unique: {len(unique_customers)}")
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        file_name = f"customers_{current_date}.json"
        output_path = os.path.join("data", "raw", file_name)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_customers, f, ensure_ascii=False, indent=2)
            
        logger.info(f"File successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Critical failure in the customer extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_customer_extraction()