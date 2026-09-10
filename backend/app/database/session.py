# uv add "sqlalchemy[asyncio]" asyncmy
# uv add cryptography

# Run in Administrator PowerShell:
# winget install Oracle.MySQL

# Get-Service *mysql*

# Get-ChildItem "C:\Program Files\MySQL" -Recurse -Filter "mysql_configurator.exe" -ErrorAction SilentlyContinue |
# Select-Object FullName

# Run this in Administrator PowerShell:
# & "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql_configurator.exe"

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import settings
from backend.app.core.exceptions import (
    ConfigurationError,
    DatabaseConnectionError,
)
from backend.app.core.logging import get_logger


logger = get_logger(__name__)


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Create and return the shared asynchronous database engine."""

    global _engine

    if _engine is not None:
        return _engine

    if settings.database_url is None:
        raise ConfigurationError(
            message="DATABASE_URL is missing from the environment."
        )

    _engine = create_async_engine(
        settings.database_url.get_secret_value(),
        echo=settings.database_echo,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_recycle=settings.database_pool_recycle_seconds,
    )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create and return the shared asynchronous session factory."""

    global _session_factory

    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    return _session_factory


async def get_database_session() -> AsyncIterator[AsyncSession]:
    """Provide one database session for a request or operation."""

    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> None:
    """Verify that MySQL is reachable."""

    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))

    except ConfigurationError:
        raise

    except Exception as exc:
        raise DatabaseConnectionError(
            details={
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
        ) from exc

    logger.info("mysql_connection_check_completed")


async def close_database_connection() -> None:
    """Close all pooled MySQL connections."""

    global _engine
    global _session_factory

    if _engine is not None:
        await _engine.dispose()

    _engine = None
    _session_factory = None


# uv run python -c "from backend.app.database.session import get_engine, get_session_factory, get_database_session; print('session.py imported successfully')"