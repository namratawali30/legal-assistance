from typing import Any


def build_source_label(
    result: dict[str, Any],
    citation_number: int,
) -> str:
    title = result.get(
        "title",
        "Unknown legal source",
    )

    provision_type = result.get(
        "provision_type",
        "provision",
    )

    provision_number = result.get(
        "provision_number",
        "",
    )

    provision_title = result.get(
        "provision_title",
    )

    page_start = result.get(
        "page_start",
    )

    page_end = result.get(
        "page_end",
    )

    parts = [
        f"[SOURCE {citation_number}]",
        title,
    ]

    if provision_number:
        parts.append(
            f"{provision_type.title()} "
            f"{provision_number}"
        )

    if provision_title:
        parts.append(
            str(provision_title)
        )

    if (
        page_start is not None
        and page_end is not None
    ):
        if page_start == page_end:
            parts.append(
                f"Page {page_start}"
            )
        else:
            parts.append(
                f"Pages {page_start}-{page_end}"
            )

    return " | ".join(parts)


def validate_retrieval_result(
    result: dict[str, Any],
) -> bool:
    required_fields = [
        "chunk_id",
        "source_id",
        "title",
        "category",
        "authority",
        "provision_type",
        "provision_number",
        "text",
    ]

    for field in required_fields:
        value = result.get(field)

        if value is None:
            return False

        if (
            isinstance(value, str)
            and not value.strip()
        ):
            return False

    return True


def deduplicate_results(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen_chunk_ids: set[str] = set()

    unique_results = []

    for result in results:
        chunk_id = result.get(
            "chunk_id"
        )

        if not chunk_id:
            continue

        if chunk_id in seen_chunk_ids:
            continue

        seen_chunk_ids.add(
            chunk_id
        )

        unique_results.append(
            result
        )

    return unique_results


def build_rag_context(
    results: list[dict[str, Any]],
    max_sources: int = 5,
) -> dict[str, Any]:
    if max_sources < 1:
        raise ValueError(
            "max_sources must be at least 1"
        )

    valid_results = [
        result
        for result in results
        if validate_retrieval_result(
            result
        )
    ]

    valid_results = (
        deduplicate_results(
            valid_results
        )
    )

    selected_results = (
        valid_results[
            :max_sources
        ]
    )

    context_blocks = []
    citation_map = {}

    allowed_citations = []

    for citation_number, result in enumerate(
        selected_results,
        start=1,
    ):
        source_label = build_source_label(
            result,
            citation_number,
        )

        citation_id = (
            f"SOURCE_{citation_number}"
        )

        allowed_citations.append(
            citation_id
        )

        citation_map[citation_id] = {
            "citation_number":
                citation_number,

            "chunk_id":
                result["chunk_id"],

            "source_id":
                result["source_id"],

            "title":
                result["title"],

            "authority":
                result["authority"],

            "category":
                result["category"],

            "subcategory":
                result.get(
                    "subcategory"
                ),

            "document_type":
                result.get(
                    "document_type"
                ),

            "provision_type":
                result[
                    "provision_type"
                ],

            "provision_number":
                result[
                    "provision_number"
                ],

            "provision_title":
                result.get(
                    "provision_title"
                ),

            "page_start":
                result.get(
                    "page_start"
                ),

            "page_end":
                result.get(
                    "page_end"
                ),

            "landing_page":
                result.get(
                    "landing_page"
                ),

            "pdf_url":
                result.get(
                    "pdf_url"
                ),

            "official_url":
                result.get(
                    "official_url"
                ),

            "source_provider":
                result.get(
                    "source_provider", "Local Knowledge Base"
                ),

            "source_mode":
                result.get(
                    "source_mode", "local"
                ),

            "fetched_at":
                result.get(
                    "fetched_at"
                ),

            "content_hash":
                result.get(
                    "content_hash"
                ),

            "score":
                result.get(
                    "score"
                ),
        }

        # Wrap text in OFFICIAL_LEGAL_SOURCE_MATERIAL delimiter for prompt injection safety
        context_block = (
            f"{source_label}\n"
            f"CITATION_ID: {citation_id}\n"
            f"AUTHORITY: {result['authority']}\n"
            f"CATEGORY: {result['category']}\n"
            f"<OFFICIAL_LEGAL_SOURCE_MATERIAL>\n"
            f"{result['text']}\n"
            f"</OFFICIAL_LEGAL_SOURCE_MATERIAL>"
        )

        context_blocks.append(
            context_block
        )

    combined_context = (
        "\n\n"
        + "=" * 80
        + "\n\n"
    ).join(
        context_blocks
    )

    return {
        "context":
            combined_context,

        "sources":
            selected_results,

        "citation_map":
            citation_map,

        "allowed_citations":
            allowed_citations,

        "source_count":
            len(selected_results),
    }