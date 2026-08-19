from typing import Any


def format_sources_for_response(
    citation_map: dict[str, dict[str, Any]],
    used_citations: list[str],
) -> list[dict[str, Any]]:
    sources = []

    seen = set()

    for citation_id in used_citations:
        if citation_id in seen:
            continue

        seen.add(
            citation_id
        )

        source = citation_map.get(
            citation_id
        )

        if not source:
            continue

        sources.append(
            {
                "citation_id":
                    citation_id,

                "title":
                    source.get(
                        "title"
                    ),

                "authority":
                    source.get(
                        "authority"
                    ),

                "provision_type":
                    source.get(
                        "provision_type"
                    ),

                "provision_number":
                    source.get(
                        "provision_number"
                    ),

                "provision_title":
                    source.get(
                        "provision_title"
                    ),

                "page_start":
                    source.get(
                        "page_start"
                    ),

                "page_end":
                    source.get(
                        "page_end"
                    ),

                "landing_page":
                    source.get(
                        "landing_page"
                    ),

                "pdf_url":
                    source.get(
                        "pdf_url"
                    ),
            }
        )

    return sources