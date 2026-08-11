"""Configuração do Alembic para o TaskFlow API.

Aponta para o ``Base.metadata`` da aplicação, permitindo autogenerate de
migrations baseado nos Models SQLAlchemy definidos em ``app/models``.

A URL do banco é lida do nosso ``Settings`` — mesma fonte de verdade
que a aplicação usa. Para sobrescrever via env, defina ``DATABASE_URL``
no ambiente ou no ``.env``.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from app.core.config import get_settings
from app.core.database import Base

# Importar models explicitamente — sem isso, ``Base.metadata`` fica vazio
# e o autogenerate não detecta nenhuma tabela.
from app.models import task  # noqa: F401
from sqlalchemy import engine_from_config, pool

# Alembic Config object (lê alembic.ini).
config = context.config

# Sobe loggers lendo o alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Fonte da verdade do schema para autogenerate.
target_metadata = Base.metadata

# Sobrescreve sqlalchemy.url do alembic.ini com o valor dos Settings.
# (Sem isso, precisaríamos duplicar a URL no alembic.ini.)
config.set_main_option("sqlalchemy.url", get_settings().database_url)


def run_migrations_offline() -> None:
    """Modo offline — emite SQL para stdout sem conectar ao banco."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo online — conecta e aplica as migrations via transação."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
