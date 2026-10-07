from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool
from app.core.config import settings
from app.database.base import Base
from app.database.url import sqlalchemy_database_url
import app.models.entities
config = context.config
migration_url = sqlalchemy_database_url(settings.direct_url or settings.database_url)
if config.config_file_name: fileConfig(config.config_file_name)
target_metadata = Base.metadata
def run_migrations_offline():
    context.configure(url=migration_url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle":"named"})
    with context.begin_transaction(): context.run_migrations()
def run_migrations_online():
    connectable = create_engine(migration_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()
if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
