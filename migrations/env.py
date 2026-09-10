import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    async_engine_from_config,
)

from backend.app.core.config import settings
from backend.app.database.base import Base
from backend.app.database.models import (
    DocumentChunkRecord,
    DocumentRecord,
    MembershipRecord,
    OrganizationRecord,
    RefreshTokenRecord,
    UserRecord,
)


config = context.config


if config.config_file_name is not None:
    fileConfig(
        config.config_file_name
    )


target_metadata = Base.metadata


def get_database_url() -> str:
    if settings.database_url is None:
        raise RuntimeError(
            "DATABASE_URL is not configured."
        )

    return settings.database_url.get_secret_value()


def run_migrations_offline() -> None:
    url = get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(
    connection: Connection,
) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(
        config.config_ini_section,
        {},
    )

    configuration[
        "sqlalchemy.url"
    ] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            do_run_migrations
        )

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(
        run_async_migrations()
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


# uv run alembic upgrade head
# uv run alembic revision --autogenerate -m "create organization membership records"
# uv run alembic upgrade head

