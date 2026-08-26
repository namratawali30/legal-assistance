from pymongo import AsyncMongoClient

from app.config import settings


database_name = settings.mongodb_database.strip()

if not database_name:
    raise RuntimeError(
        "MONGODB_DATABASE must not be empty."
    )


client = AsyncMongoClient(
    settings.mongodb_url
)

database = client[
    database_name
]


async def check_database_connection() -> bool:
    try:
        await client.admin.command(
            "ping"
        )
        return True

    except Exception:
        return False


async def close_database_connection() -> None:
    await client.close()