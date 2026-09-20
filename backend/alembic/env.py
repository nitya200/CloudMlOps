"""Alembic environment.

Pulls the connection URL and the target metadata from the application itself,
so ``alembic upgrade head`` always targets the same database the API will use
and autogenerate always compares against the live models.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import pool

from alembic import context
from app.core.config import settings
from app.models import Base

config = context.config

# An explicit URL (set by the test suite, or with `-x`) wins; otherwise fall
# back to the application settings so the CLI needs no arguments.
# Alembic loads alembic.ini through ConfigParser, which treats ``%`` as
# interpolation syntax — percent-encoded passwords (``%21``) must be doubled.
if not config.get_main_option("sqlalchemy.url", None):
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or settings.database_url


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it (``alembic upgrade --sql``)."""
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Use the application engine so IAM auth tokens and SSL settings match runtime.
    from app.core.database import build_engine

    connectable = build_engine(_url(), echo=settings.db_echo, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Catch column type drift, which is exactly the class of bug that
            # let uppercase enum values reach a lowercase CHECK constraint.
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
