import re
from typing import Iterable


EVIDENCE_CITATION_PATTERN = re.compile(
    r"\[EVIDENCE_(\d+)\]",
    flags=re.IGNORECASE,
)


EVIDENCE_LIKE_PATTERN = re.compile(
    r"\[EVIDENCE_[^\]]+\]",
    flags=re.IGNORECASE,
)


def normalize_evidence_citation(
    number: str,
) -> str:
    return (
        f"EVIDENCE_{int(number)}"
    )


def extract_evidence_citations(
    text: str,
) -> list[str]:
    """
    Extract valid [EVIDENCE_n] markers while
    preserving first-occurrence order.
    """

    citations: list[str] = []
    seen: set[str] = set()

    for match in EVIDENCE_CITATION_PATTERN.finditer(
        text or ""
    ):
        citation = normalize_evidence_citation(
            match.group(1)
        )

        if citation in seen:
            continue

        seen.add(
            citation
        )

        citations.append(
            citation
        )

    return citations


def extract_malformed_evidence_markers(
    text: str,
) -> list[str]:
    """
    Find strings that resemble evidence citations
    but are not valid [EVIDENCE_<integer>] markers.
    """

    malformed: list[str] = []

    for match in EVIDENCE_LIKE_PATTERN.finditer(
        text or ""
    ):
        marker = match.group(0)

        if EVIDENCE_CITATION_PATTERN.fullmatch(
            marker
        ):
            continue

        if marker not in malformed:
            malformed.append(
                marker
            )

    return malformed


def normalize_allowed_citations(
    allowed_citations: Iterable[str],
) -> set[str]:
    normalized: set[str] = set()

    for citation in allowed_citations:
        value = str(
            citation
        ).strip().upper()

        match = re.fullmatch(
            r"EVIDENCE_(\d+)",
            value,
        )

        if not match:
            continue

        normalized.add(
            normalize_evidence_citation(
                match.group(1)
            )
        )

    return normalized


def validate_evidence_citations(
    answer: str,
    allowed_citations: Iterable[str],
) -> dict:
    """
    Validate evidence citations appearing in generated
    text.

    Evidence citations are optional: the model does not
    have to use uploaded evidence.

    However, every [EVIDENCE_n] marker that does appear
    must correspond to evidence actually supplied to the
    model.
    """

    found = extract_evidence_citations(
        answer
    )

    malformed = (
        extract_malformed_evidence_markers(
            answer
        )
    )

    allowed = normalize_allowed_citations(
        allowed_citations
    )

    valid_citations = [
        citation
        for citation in found
        if citation in allowed
    ]

    invalid_citations = [
        citation
        for citation in found
        if citation not in allowed
    ]

    valid = (
        not invalid_citations
        and not malformed
    )

    return {
        "valid":
            valid,

        "found":
            found,

        "valid_citations":
            valid_citations,

        "invalid_citations":
            invalid_citations,

        "malformed_markers":
            malformed,
    }