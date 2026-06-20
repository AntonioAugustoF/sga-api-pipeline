import requests
from infra.config import config
from infra.logger import get_logger
from infra.retry import with_retry

logger = get_logger(__name__)


@with_retry()
def authenticate_user() -> str:
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

    logger.info(f"Authentication successful. Status code: {response.status_code}")

    return response.json()["token_usuario"]