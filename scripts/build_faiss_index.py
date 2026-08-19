from app.rag.index_builder import build_faiss_index


def main():
    print()
    print("Building Legal FAISS Index")
    print("=" * 50)

    result = build_faiss_index()

    print(
        "Vectors:",
        result["vectors"],
    )

    print(
        "Dimension:",
        result["dimension"],
    )

    print(
        "Index:",
        result["index_path"],
    )

    print(
        "Metadata:",
        result["metadata_path"],
    )


if __name__ == "__main__":
    main()