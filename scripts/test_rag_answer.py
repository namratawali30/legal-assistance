from app.rag.answer_generator import (
    generate_legal_answer,
)


async def main():
    print()
    print("Legal RAG Answer Test")
    print("=" * 60)

    question = input(
        "Enter legal question: "
    ).strip()

    if not question:
        print(
            "Question cannot be empty."
        )
        return

    category = input(
        "Category (leave blank for all): "
    ).strip()

    if not category:
        category = None

    result = await generate_legal_answer(
        question=question,
        category=category,
        top_k=5,
    )

    print()
    print("ANSWER")
    print("=" * 60)
    print(
        result["answer"]
    )

    print()
    print("SOURCES")
    print("=" * 60)

    for source in result["sources"]:
        print()
        print(
            source["citation_id"],
            "-",
            source["title"],
        )

        print(
            "Authority:",
            source["authority"],
        )

        print(
            "Provision:",
            source["provision_type"],
            source["provision_number"],
        )

        if source.get(
            "provision_title"
        ):
            print(
                "Title:",
                source[
                    "provision_title"
                ],
            )

        print(
            "Pages:",
            source["page_start"],
            "-",
            source["page_end"],
        )

    print()
    print(
        "Citation validation:",
        result[
            "citation_validation"
        ],
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())