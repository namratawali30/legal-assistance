import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]

PARSED_DIR = (
    BASE_DIR
    / "knowledge_base"
    / "parsed"
)


def load_parsed_documents() -> list[tuple[Path, dict[str, Any]]]:
    documents = []

    for path in PARSED_DIR.rglob("*.json"):
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        documents.append(
            (
                path,
                data,
            )
        )

    return documents


def validate_document(
    path: Path,
    document: dict[str, Any],
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    source_id = document.get(
        "source_id"
    )

    sections = document.get(
        "sections",
        []
    )

    if not source_id:
        issues.append(
            {
                "severity": "error",
                "type": "missing_source_id",
                "message": "Document has no source_id",
            }
        )

    if not sections:
        issues.append(
            {
                "severity": "error",
                "type": "zero_sections",
                "message": "Document contains zero parsed provisions",
            }
        )

    seen_numbers: set[str] = set()

    for index, section in enumerate(sections):
        number = str(
            section.get(
                "section_number",
                ""
            )
        ).strip()

        title = section.get(
            "section_title"
        )

        text = str(
            section.get(
                "text",
                ""
            )
        ).strip()

        provision_type = section.get(
            "provision_type",
            "section",
        )

        page_start = section.get(
            "page_start"
        )

        page_end = section.get(
            "page_end"
        )

        label = (
            number
            or f"index_{index}"
        )

        if not number:
            issues.append(
                {
                    "severity": "error",
                    "type": "missing_number",
                    "provision": label,
                    "message": "Provision has no section/provision number",
                }
            )

        if number in seen_numbers:
            issues.append(
                {
                    "severity": "warning",
                    "type": "duplicate_number",
                    "provision": label,
                    "message": (
                        f"Duplicate provision number: {number}"
                    ),
                }
            )

        seen_numbers.add(number)

        if not text:
            issues.append(
                {
                    "severity": "error",
                    "type": "empty_text",
                    "provision": label,
                    "message": "Provision text is empty",
                }
            )

        text_length = len(text)

        if 0 < text_length < 40:
            issues.append(
                {
                    "severity": "warning",
                    "type": "suspiciously_short",
                    "provision": label,
                    "message": (
                        f"Provision text is only {text_length} characters"
                    ),
                }
            )

        if text_length > 20000:
            issues.append(
                {
                    "severity": "warning",
                    "type": "suspiciously_long",
                    "provision": label,
                    "message": (
                        f"Provision text is {text_length} characters"
                    ),
                }
            )

        if page_start is None:
            issues.append(
                {
                    "severity": "error",
                    "type": "missing_page_start",
                    "provision": label,
                    "message": "page_start is missing",
                }
            )

        if page_end is None:
            issues.append(
                {
                    "severity": "error",
                    "type": "missing_page_end",
                    "provision": label,
                    "message": "page_end is missing",
                }
            )

        if (
            isinstance(page_start, int)
            and isinstance(page_end, int)
            and page_end < page_start
        ):
            issues.append(
                {
                    "severity": "error",
                    "type": "invalid_page_range",
                    "provision": label,
                    "message": (
                        f"page_end {page_end} "
                        f"is before page_start {page_start}"
                    ),
                }
            )

        if provision_type == "section" and not title:
            issues.append(
                {
                    "severity": "warning",
                    "type": "missing_section_title",
                    "provision": label,
                    "message": "Statutory section has no title",
                }
            )

    errors = [
        issue
        for issue in issues
        if issue["severity"] == "error"
    ]

    warnings = [
        issue
        for issue in issues
        if issue["severity"] == "warning"
    ]

    return {
        "source_id": source_id,
        "file": str(path),
        "provisions": len(sections),
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "status": (
            "failed"
            if errors
            else "passed"
        ),
    }


def validate_corpus() -> dict[str, Any]:
    documents = load_parsed_documents()

    results = []

    seen_source_ids: set[str] = set()

    corpus_issues: list[dict[str, Any]] = []

    for path, document in documents:
        source_id = document.get(
            "source_id"
        )

        if source_id in seen_source_ids:
            corpus_issues.append(
                {
                    "severity": "error",
                    "type": "duplicate_source_id",
                    "source_id": source_id,
                    "message": (
                        f"Duplicate source_id found: {source_id}"
                    ),
                }
            )

        seen_source_ids.add(
            source_id
        )

        results.append(
            validate_document(
                path,
                document,
            )
        )

    total_provisions = sum(
        result["provisions"]
        for result in results
    )

    total_errors = sum(
        result["error_count"]
        for result in results
    )

    total_warnings = sum(
        result["warning_count"]
        for result in results
    )

    corpus_errors = [
        issue
        for issue in corpus_issues
        if issue["severity"] == "error"
    ]

    total_errors += len(
        corpus_errors
    )

    return {
        "documents": len(results),
        "total_provisions": total_provisions,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "corpus_issues": corpus_issues,
        "results": results,
        "status": (
            "passed"
            if total_errors == 0
            else "failed"
        ),
    }