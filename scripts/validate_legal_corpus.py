import json

from app.legal.corpus_validator import validate_corpus


def main():
    report = validate_corpus()

    print()
    print("Legal Corpus Validation")
    print("=" * 60)

    print(
        "Documents:",
        report["documents"],
    )

    print(
        "Total provisions:",
        report["total_provisions"],
    )

    print(
        "Errors:",
        report["total_errors"],
    )

    print(
        "Warnings:",
        report["total_warnings"],
    )

    print(
        "Status:",
        report["status"].upper(),
    )

    print()
    print("Document Results")
    print("-" * 60)

    for result in report["results"]:
        print()
        print(
            result["source_id"],
            "->",
            result["status"],
        )

        print(
            "   Provisions:",
            result["provisions"],
        )

        print(
            "   Errors:",
            result["error_count"],
        )

        print(
            "   Warnings:",
            result["warning_count"],
        )

        for issue in result["errors"][:10]:
            print(
                "   ERROR:",
                issue["type"],
                "|",
                issue.get(
                    "provision",
                    "",
                ),
                "|",
                issue["message"],
            )

        for issue in result["warnings"][:10]:
            print(
                "   WARNING:",
                issue["type"],
                "|",
                issue.get(
                    "provision",
                    "",
                ),
                "|",
                issue["message"],
            )

    if report["corpus_issues"]:
        print()
        print("Corpus-level issues")
        print("-" * 60)

        for issue in report["corpus_issues"]:
            print(
                issue["severity"].upper(),
                issue["type"],
                issue["message"],
            )

    output_path = (
        "knowledge_base/"
        "manifest/"
        "validation_report.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(
        "Validation report saved to:",
        output_path,
    )


if __name__ == "__main__":
    main()