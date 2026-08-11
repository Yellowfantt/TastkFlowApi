"""Atalho para subir a aplicação em desenvolvimento.

Uso:
    python run.py

Lê host/porta do ``Settings`` (que vem do .env). Equivalente a:
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
mas com a vantagem de carregar as configurações do nosso módulo.

Em produção, prefira chamar o uvicorn diretamente:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from __future__ import annotations

import uvicorn
from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )


if __name__ == "__main__":
    main()
