"""Configurações da aplicação, carregadas de variáveis de ambiente / .env.

Este módulo NÃO acessa o banco de dados. Ele apenas lê e valida
configurações (URL do banco, porta, ambiente) usando ``pydantic-settings``.

Por que ``pydantic-settings``?
    É o módulo oficial do Pydantic para esse fim. Tipagem forte, validação
    automática e suporte nativo a ``.env`` — sem precisar de ``python-dotenv``
    manual.

Por que ``lru_cache`` no getter?
    As configurações não mudam durante a execução. Cachear evita reler o
    ``.env`` e reinstanciar o objeto a cada ``get_settings()``.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação."""

    # Ambiente de execução: development | production.
    # Útil para ligar/desligar comportamentos (ex.: logs verbosos, CORS).
    app_env: str = Field(default="development", alias="APP_ENV")

    # URL de conexão com o banco. Para SQLite local, ``sqlite:///./taskflow.db``.
    database_url: str = Field(default="sqlite:///./taskflow.db", alias="DATABASE_URL")

    # Configurações do servidor ASGI (informativas; o comando real fica em run.py / uvicorn).
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Ignora variáveis extras no .env que não estejam declaradas aqui,
        # em vez de falhar a validação.
        extra="ignore",
        # Permite popular os campos tanto pelo nome do atributo quanto pelo alias
        # (ex.: ``database_url`` ou ``DATABASE_URL``).
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna a instância cacheada de ``Settings``.

    Cache evita reler o ``.env`` e revalidar a cada chamada.
    """
    return Settings()
