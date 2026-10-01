from app.rag.evidence_citation_guard import (
    extract_evidence_citations,
    extract_malformed_evidence_markers,
    validate_evidence_citations,
)


def test_extracts_evidence_citations():
    text = (
        "The invoice records the purchase "
        "[EVIDENCE_1], while the payment "
        "receipt supports the amount "
        "[EVIDENCE_2]."
    )

    citations = extract_evidence_citations(
        text
    )

    assert citations == [
        "EVIDENCE_1",
        "EVIDENCE_2",
    ]


def test_duplicate_citations_are_deduplicated():
    text = (
        "Invoice [EVIDENCE_1]. "
        "Again [EVIDENCE_1]."
    )

    citations = extract_evidence_citations(
        text
    )

    assert citations == [
        "EVIDENCE_1"
    ]


def test_evidence_citations_are_case_insensitive():
    text = (
        "Invoice [evidence_1]. "
        "Receipt [Evidence_2]."
    )

    citations = extract_evidence_citations(
        text
    )

    assert citations == [
        "EVIDENCE_1",
        "EVIDENCE_2",
    ]


def test_known_evidence_citation_is_valid():
    result = validate_evidence_citations(
        answer=(
            "The invoice records payment "
            "of INR 25,000. [EVIDENCE_1]"
        ),
        allowed_citations=[
            "EVIDENCE_1",
        ],
    )

    assert result[
        "valid"
    ] is True

    assert result[
        "invalid_citations"
    ] == []

    assert result[
        "malformed_markers"
    ] == []


def test_unknown_evidence_citation_is_rejected():
    result = validate_evidence_citations(
        answer=(
            "The invoice establishes payment. "
            "[EVIDENCE_999]"
        ),
        allowed_citations=[
            "EVIDENCE_1",
        ],
    )

    assert result[
        "valid"
    ] is False

    assert result[
        "invalid_citations"
    ] == [
        "EVIDENCE_999"
    ]


def test_malformed_evidence_marker_is_rejected():
    result = validate_evidence_citations(
        answer=(
            "The invoice is relevant "
            "[EVIDENCE_INVOICE]."
        ),
        allowed_citations=[
            "EVIDENCE_1",
        ],
    )

    assert result[
        "valid"
    ] is False

    assert result[
        "malformed_markers"
    ] == [
        "[EVIDENCE_INVOICE]"
    ]


def test_no_evidence_citation_is_valid():
    result = validate_evidence_citations(
        answer=(
            "The complaint is based only "
            "on the user's stated facts."
        ),
        allowed_citations=[
            "EVIDENCE_1",
        ],
    )

    assert result[
        "valid"
    ] is True

    assert result[
        "found"
    ] == []


def test_evidence_citation_is_invalid_when_no_evidence_supplied():
    result = validate_evidence_citations(
        answer=(
            "The document proves payment. "
            "[EVIDENCE_1]"
        ),
        allowed_citations=[],
    )

    assert result[
        "valid"
    ] is False

    assert result[
        "invalid_citations"
    ] == [
        "EVIDENCE_1"
    ]