from sqlalchemy import create_engine
from infra.config import config
from urllib.parse import quote_plus

def get_db_engine():
    """
    Cria e retorna o objeto engine de conexão com o banco de dados
    utilizando as credenciais centralizadas no config.py.
    """
    try:
        connection_url = (
    f"postgresql://{config.DB_USER}:{quote_plus(config.DB_PASSWORD)}"
    f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
)

        # cria a engine de conexão
        engine = create_engine(connection_url)
        return engine

    except Exception as e:
        print(f"❌ erro ao configurar a engine do banco de dados: {e}")
        raise

# teste rápido de conexão para garantir que está tudo funcionando
if __name__ == "__main__":
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            print("✨ Conexão com o banco de dados realizada com sucesso.")
    except Exception as e:
        print("🚨 Falha crítica no teste de conexão.")
        raise