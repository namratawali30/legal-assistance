import asyncio

from app.database import database
from app.db.collections import (
    EVIDENCE_COLLECTION,
)


async def main():
    collection = database[
        EVIDENCE_COLLECTION
    ]

    pipeline = [
        {
            "$group": {
                "_id": {
                    "user_id":
                        "$user_id",

                    "complaint_id":
                        "$complaint_id",

                    "sha256":
                        "$sha256",
                },

                "count": {
                    "$sum": 1
                },

                "ids": {
                    "$push": "$_id"
                },
            }
        },
        {
            "$match": {
                "count": {
                    "$gt": 1
                }
            }
        },
    ]

    # PyMongo AsyncMongoClient requires
    # aggregate() itself to be awaited.
    cursor = await collection.aggregate(
        pipeline
    )

    duplicates = await cursor.to_list(
        length=None
    )

    if not duplicates:
        print(
            "No duplicate evidence records found."
        )
        return

    print(
        f"Found {len(duplicates)} "
        "duplicate evidence group(s):"
    )

    for duplicate in duplicates:
        print(
            duplicate
        )


if __name__ == "__main__":
    asyncio.run(
        main()
    )