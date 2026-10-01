import re
from typing import Any


CITATION_PATTERN = re.compile(
    r"\[(SOURCE_\d+)\]"
)


def extract_citations(
    text: str,
) -> list[str]:
    return CITATION_PATTERN.findall(
        text
    )


def validate_citations(
    answer: str,
    allowed_citations: list[str],
) -> dict[str, Any]:
    found = extract_citations(
        answer
    )

    allowed = set(
        allowed_citations
    )

    invalid = [
        citation
        for citation in found
        if citation not in allowed
    ]

    valid = [
        citation
        for citation in found
        if citation in allowed
    ]

    return {
        "valid":
            len(invalid) == 0,

        "found":
            found,

        "valid_citations":
            valid,

        "invalid_citations":
            invalid,
    }


def ensure_answer_has_citation(
    answer: str,
    allowed_citations: list[str],
) -> bool:
    validation = validate_citations(
        answer,
        allowed_citations,
    )

    return (
        validation["valid"]
        and len(
            validation[
                "valid_citations"
            ]
        ) > 0
    )