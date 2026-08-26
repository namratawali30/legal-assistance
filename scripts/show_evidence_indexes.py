import asyncio

from app.repositories.evidence_repository import (
    evidence_collection,
)


async def main():
    indexes = await evidence_collection.index_information()

    for name, definition in indexes.items():
        print(
            name,
            definition,
        )


if __name__ == "__main__":
    asyncio.run(
        main()
    )