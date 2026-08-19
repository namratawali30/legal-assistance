from app.legal.section_parser import parse_all_sources


def main():
    results = parse_all_sources()

    print()
    print("Legal section parsing results")
    print("=" * 60)

    total_sections = 0

    for result in results:
        print(
            result["source_id"],
            "->",
            result["status"],
        )

        if result["status"] == "parsed":
            print(
                "   Sections:",
                result["sections"],
            )

            print(
                "   Output:",
                result["output"],
            )

            total_sections += result["sections"]

        else:
            print(
                "   Error:",
                result["error"],
            )

    print()
    print(
        "Total parsed sections:",
        total_sections,
    )


if __name__ == "__main__":
    main()