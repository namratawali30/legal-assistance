from typing import Any

from app.database import database
from app.db.collections import (
    LEGAL_DOCUMENTS_COLLECTION,
    RESOURCES_COLLECTION,
)


legal_documents_collection = database[LEGAL_DOCUMENTS_COLLECTION]
resources_collection = database[RESOURCES_COLLECTION]


async def create_legal_document(
    document_data: dict[str, Any],
):
    result = await legal_documents_collection.insert_one(
        document_data
    )

    return result.inserted_id


async def get_legal_documents_by_category(
    category: str,
) -> list[dict[str, Any]]:
    cursor = legal_documents_collection.find(
        {
            "category": category,
            "is_active": True,
        }
    ).sort(
        "updated_at",
        -1,
    )

    return await cursor.to_list(length=100)


async def create_resource(
    resource_data: dict[str, Any],
):
    result = await resources_collection.insert_one(
        resource_data
    )

    return result.inserted_id


async def get_resources_by_category(
    category: str,
) -> list[dict[str, Any]]:
    cursor = resources_collection.find(
        {
            "category": category,
            "is_active": True,
        }
    ).sort(
        "updated_at",
        -1,
    )

    return await cursor.to_list(length=100)