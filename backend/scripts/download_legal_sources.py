import asyncio

from app.legal.downloader import download_all_sources


async def main():
    results = await download_all_sources()

    print()
    print("Legal source download results")
    print("=" * 50)

    for result in results:
        print(
            result["source_id"],
            "->",
            result["status"],
        )

        if result["status"] == "failed":
            print(
                "   Error:",
                result["error"],
            )


if __name__ == "__main__":
    asyncio.run(main())
    