import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente do Python
load_dotenv()

class Config:
    """Gerenciador de configurações e variáveis de ambiente do pipeline."""

    # ====================================
    # 1. ACESSO AO BANCO DE DADOS (DB)
    # ====================================
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    # ====================================
    # 2. ACESSO AO SISTEMA ORIGEM
    # ====================================
    SYSTEM_URL = os.getenv("SYSTEM_URL")
    SYSTEM_USER = os.getenv("SYSTEM_USER")
    SYSTEM_PASSWORD = os.getenv("SYSTEM_PASSWORD")

    # ====================================
    # 3. ACESSO À API
    # ====================================
    API_BASE_URL = os.getenv("API_BASE_URL")
    API_KEY = os.getenv("API_KEY")

# Instância única para ser importada e utilizada nos outros módulos
config = Config()