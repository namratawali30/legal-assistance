from app.rag.retriever import (
    search_legal_chunks,
)


def main():
    print()
    print("Legal Semantic Retrieval Test")
    print("=" * 60)

    query = input(
        "Enter legal question: "
    ).strip()

    if not query:
        print("Question cannot be empty.")
        return

    results = search_legal_chunks(
        query=query,
        top_k=5,
    )

    print()
    print(
        f"Top {len(results)} results"
    )
    print("=" * 60)

    for position, result in enumerate(
        results,
        start=1,
    ):
        print()
        print(
            f"RESULT {position}"
        )

        print(
            "Score:",
            round(
                result["score"],
                4,
            ),
        )

        print(
            "Source:",
            result["title"],
        )

        print(
            "Category:",
            result["category"],
        )

        print(
            "Authority:",
            result["authority"],
        )

        print(
            "Provision type:",
            result["provision_type"],
        )

        print(
            "Provision:",
            result["provision_number"],
        )

        if result.get(
            "provision_title"
        ):
            print(
                "Title:",
                result["provision_title"],
            )

        print(
            "Pages:",
            f"{result['page_start']}"
            f"-{result['page_end']}",
        )

        print()
        print("TEXT:")
        print(
            result["text"][:1200]
        )

        print()
        print("-" * 60)


if __name__ == "__main__":
    main()