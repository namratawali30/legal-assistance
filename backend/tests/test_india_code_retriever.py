import pytest
from unittest.mock import AsyncMock, patch
import httpx

from app.services.india_code_retriever import (
    compute_content_hash,
    is_safe_url,
    parse_dspace_objects,
    search_india_code,
)


def test_ssrf_safety_guard():
    assert is_safe_url("https://indiacode.gov.in/server/api/discover/search/objects") is True
    assert is_safe_url("https://www.indiacode.nic.in/handle/1234") is True
    assert is_safe_url("http://indiacode.gov.in/something") is False  # Non-HTTPS
    assert is_safe_url("https://malicious-site.com/steal") is False   # Untrusted host
    assert is_safe_url("https://169.254.169.254/latest/meta-data/") is False


def test_compute_content_hash():
    h1 = compute_content_hash("  The Consumer Protection   Act, 2019  ")
    h2 = compute_content_hash("The Consumer Protection Act, 2019")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 length


def test_parse_dspace_objects():
    mock_data = {
        "_embedded": {
            "searchResult": {
                "_embedded": {
                    "objects": [
                        {
                            "_embedded": {
                                "indexableObject": {
                                    "name": "The Consumer Protection Act, 2019",
                                    "handle": "123456789/1512",
                                    "metadata": {
                                        "dc.title.act_name": [{"value": "Consumer Protection Act, 2019"}],
                                        "dc.identifier.state_name": [{"value": "CENTRAL"}],
                                        "dc.identifier.act_number": [{"value": "35"}],
                                        "dc.date.act_year": [{"value": "2019"}],
                                        "dc.identifier.collection": [{"value": "ACT"}],
                                    },
                                }
                            }
                        }
                    ]
                }
            }
        }
    }

    results = parse_dspace_objects(mock_data)
    assert len(results) == 1
    assert results[0]["title"] == "Consumer Protection Act, 2019"
    assert results[0]["source_provider"] == "India Code"
    assert results[0]["official_url"] == "https://indiacode.gov.in/handle/123456789/1512"
    assert results[0]["content_hash"] is not None


@pytest.mark.anyio
async def test_search_india_code_timeout_handled_safely():
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        results = await search_india_code("consumer protection")
        assert results == []  # Handled safely, returns empty list without crashing


@pytest.mark.anyio
async def test_search_india_code_connection_failure_handled_safely():
    with patch("httpx.AsyncClient.get", side_effect=httpx.RequestError("Connection failed")):
        results = await search_india_code("consumer protection")
        assert results == []


@pytest.mark.anyio
async def test_search_india_code_non_200_handled_safely():
    mock_resp = AsyncMock()
    mock_resp.status_code = 500
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        results = await search_india_code("consumer protection")
        assert results == []
