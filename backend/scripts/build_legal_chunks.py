from app.legal.chunk_builder import (
    build_all_chunks,
    save_chunks,
)


def main():
    chunks = build_all_chunks()

    output_path = save_chunks(
        chunks
    )

    print()
    print("Legal Chunk Builder")
    print("=" * 50)

    print(
        "Total chunks:",
        len(chunks),
    )

    print(
        "Output:",
        output_path,
    )

    categories = {}

    for chunk in chunks:
        category = chunk[
            "category"
        ]

        categories[category] = (
            categories.get(
                category,
                0,
            )
            + 1
        )

    print()
    print("Chunks by category")

    for category, count in sorted(
        categories.items()
    ):
        print(
            f"  {category}: {count}"
        )


if __name__ == "__main__":
    main()