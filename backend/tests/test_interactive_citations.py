import pytest

from app.rag.prompt import LEGAL_SYSTEM_INSTRUCTIONS, SIMPLE_SYSTEM_INSTRUCTIONS
from app.rag.source_formatter import format_sources_for_response


def test_system_prompt_contains_multi_source_rules():
    # Citation grouping rules live in base LEGAL_SYSTEM_INSTRUCTIONS
    assert "GROUPING:" in LEGAL_SYSTEM_INSTRUCTIONS
    # Simple mode contains citation format rules
    assert "[SOURCE_1]" in SIMPLE_SYSTEM_INSTRUCTIONS
    assert "[SOURCE_2]" in SIMPLE_SYSTEM_INSTRUCTIONS


def test_source_formatter_trims_sources_to_max_three():
    citation_map = {
        "SOURCE_1": {
            "title": "Consumer Protection Act, 2019",
            "authority": "District Forum",
            "provision_type": "section",
            "provision_number": "35",
            "source_provider": "India Code",
            "source_mode": "live",
        },
        "SOURCE_2": {
            "title": "Consumer Protection Rules, 2020",
            "authority": "Central Government",
            "provision_type": "rule",
            "provision_number": "4",
            "source_provider": "India Code",
            "source_mode": "live",
        },
        "SOURCE_3": {
            "title": "Consumer Protection Regulations",
            "authority": "Central Authority",
            "provision_type": "regulation",
            "provision_number": "2",
            "source_provider": "India Code",
            "source_mode": "live",
        },
        "SOURCE_4": {
            "title": "Unrelated Act",
            "authority": "State Government",
            "provision_type": "section",
            "provision_number": "10",
            "source_provider": "Local Knowledge Base",
            "source_mode": "local",
        },
    }

    used_citations = ["SOURCE_1", "SOURCE_2", "SOURCE_3", "SOURCE_4"]
    formatted = format_sources_for_response(citation_map, used_citations)

    # Multi-Source Rule: Max 3 sources formatted for output!
    assert len(formatted) == 3
    assert formatted[0]["citation_id"] == "SOURCE_1"
    assert formatted[1]["citation_id"] == "SOURCE_2"
    assert formatted[2]["citation_id"] == "SOURCE_3"

