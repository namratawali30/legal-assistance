from pymongo import AsyncMongoClient

from app.config import settings


client = AsyncMongoClient(settings.mongodb_url)

database = client[settings.mongodb_database]


async def check_database_connection() -> bool:
    try:
        await client.admin.command("ping")
        return True
    except Exception:
        return False


async def close_database_connection() -> None:
    await client.close()