import requests
from infra.config import config

def authenticate_user():
    """Authenticates the user against the system API and returns the user token."""
    url = f"{config.API_BASE_URL}/usuario/autenticar"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.API_KEY}"
    }
    payload = {
        "usuario": config.SYSTEM_USER,
        "senha": config.SYSTEM_PASSWORD
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    print("Status code:", response.status_code)
    print("Resposta bruta:", response.text)
    return response.json()["token_usuario"]