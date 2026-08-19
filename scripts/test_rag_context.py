from app.rag.context_builder import (
    build_rag_context,
)
from app.rag.retriever import (
    search_legal_chunks,
)


def main():
    query = input(
        "Enter legal question: "
    ).strip()

    if not query:
        print(
            "Question cannot be empty."
        )
        return

    results = search_legal_chunks(
        query=query,
        top_k=5,
    )

    rag_context = build_rag_context(
        results,
        max_sources=5,
    )

    print()
    print("RAG CONTEXT")
    print("=" * 80)
    print()
    print(
        rag_context[
            "context"
        ]
    )

    print()
    print("=" * 80)

    print(
        "Allowed citations:",
        rag_context[
            "allowed_citations"
        ],
    )

    print(
        "Source count:",
        rag_context[
            "source_count"
        ],
    )


if __name__ == "__main__":
    main()