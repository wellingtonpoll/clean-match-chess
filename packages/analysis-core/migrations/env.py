"""Alembic environment for the analysis-core schema.

Resolves the database URL from `DATABASE_URL` at runtime (psycopg sync
driver is used for migrations — async + alembic combination is fiddly,
and migrations are short-lived synchronous operations anyway). The
runtime audit pipeline uses the async psycopg driver via
`analysis_core.db.session`.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import the declarative Base + register the AuditRunModel so
# autogenerate sees the metadata.
from analysis_core.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _resolve_url() -> str:
    """Resolve DATABASE_URL with a dev-safe default."""
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch",
    )
    # Alembic + psycopg sync driver: use `postgresql+psycopg://` (works
    # for both sync and async psycopg 3). No URL rewriting needed.
    return url


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — no live database connection."""
    url = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _resolve_url()

    connectable = engine_from_config(
        configuration,
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
