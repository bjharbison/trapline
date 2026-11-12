"""Migration configuration uses the same engine factory as the application."""

from logging.config import fileConfig

from alembic import context

from trapline_api.database import make_engine
from trapline_api.models import Base

config = context.config
if config.config_file_name and config.get_section(config.config_ini_section, {}).get("loggers"):
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if url == "sqlite://":
        raise RuntimeError("Offline migration SQL requires an explicit sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = make_engine()
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
