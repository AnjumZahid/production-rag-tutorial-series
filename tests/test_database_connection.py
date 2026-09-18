import asyncio

from backend.app.core.exceptions import AppError
from backend.app.database.session import (
    check_database_connection,
    close_database_connection,
)


async def main() -> None:
    try:
        await check_database_connection()
        print("MySQL connection test passed successfully.")

    except AppError as exc:
        print("\nMySQL connection test failed.")
        print("Code:", exc.code)
        print("Message:", exc.message)

        if exc.details:
            print("Details:", exc.details)

    finally:
        await close_database_connection()


if __name__ == "__main__":
    asyncio.run(main())



# uv run python -m tests.test_database_connection