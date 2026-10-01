from app.legal.pdf_extractor import extract_all_sources


def main():
    results = extract_all_sources()

    print()
    print("Legal PDF extraction results")
    print("=" * 60)

    for result in results:
        print(
            result["source_id"],
            "->",
            result["status"],
        )

        if result["status"] == "extracted":
            print(
                "   Pages:",
                result["pages"],
            )
            print(
                "   Output:",
                result["output"],
            )

        else:
            print(
                "   Error:",
                result["error"],
            )


if __name__ == "__main__":
    main()