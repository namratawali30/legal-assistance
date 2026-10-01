import hashlib
import json
import logging
import time
from urllib.parse import urlparse
import httpx

logger = logging.getLogger(__name__)

ALLOWED_HOSTS = {"indiacode.gov.in", "indiacode.nic.in", "www.indiacode.nic.in"}
INDIA_CODE_SEARCH_API = "https://indiacode.gov.in/server/api/discover/search/objects"
TIMEOUT_SECONDS = 5.0
MAX_RESPONSE_BYTES = 1_000_000  # 1MB max response size

# Bounded in-memory cache: query -> { "timestamp": float, "data": list[dict] }
_CACHE: dict[str, dict] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour TTL


def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return False
        if parsed.hostname not in ALLOWED_HOSTS:
            return False
        return True
    except Exception:
        return False


def compute_content_hash(text: str) -> str:
    normalized = " ".join((text or "").strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_cached_results(query: str) -> list[dict] | None:
    cache_key = query.strip().lower()
    entry = _CACHE.get(cache_key)
    if not entry:
        return None
    if time.time() - entry["timestamp"] > CACHE_TTL_SECONDS:
        return None
    return entry["data"]


def set_cached_results(query: str, data: list[dict]):
    cache_key = query.strip().lower()
    if len(_CACHE) > 500:
        # Evict oldest entries if cache reaches limit
        oldest_keys = sorted(_CACHE.keys(), key=lambda k: _CACHE[k]["timestamp"])[:100]
        for k in oldest_keys:
            _CACHE.pop(k, None)
    _CACHE[cache_key] = {
        "timestamp": time.time(),
        "data": data,
    }


def parse_dspace_objects(data: dict) -> list[dict]:
    results = []
    try:
        objects = (
            data.get("_embedded", {})
            .get("searchResult", {})
            .get("_embedded", {})
            .get("objects", [])
        )
        for idx, obj in enumerate(objects[:5]):
            indexable = obj.get("_embedded", {}).get("indexableObject", {})
            name = indexable.get("name") or obj.get("hitHighlights", {}).get("dc.title", [""])[0]
            if not name:
                continue

            metadata = indexable.get("metadata", {})
            handle = indexable.get("handle") or ""

            act_name_meta = metadata.get("dc.title.act_name", [{}])[0].get("value") or name
            state_meta = metadata.get("dc.identifier.state_name", [{}])[0].get("value") or "CENTRAL"
            act_num_meta = metadata.get("dc.identifier.act_number", [{}])[0].get("value") or ""
            act_year_meta = metadata.get("dc.date.act_year", [{}])[0].get("value") or ""
            collection_meta = metadata.get("dc.identifier.collection", [{}])[0].get("value") or "ACT"

            official_url = f"https://indiacode.gov.in/handle/{handle}" if handle else "https://indiacode.gov.in/"
            content_text = f"{name}. {act_name_meta} (Act No. {act_num_meta} of {act_year_meta}). Authority: {state_meta}."
            content_hash = compute_content_hash(content_text)
            fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            results.append({
                "chunk_id": f"live_ic_{handle.replace('/', '_') or idx}",
                "source_id": f"IC_{handle.replace('/', '_') or idx}",
                "title": act_name_meta,
                "authority": f"India Code · {state_meta}",
                "category": "consumer_rights",
                "provision_type": collection_meta.lower(),
                "provision_number": act_num_meta or "N/A",
                "provision_title": name,
                "text": content_text,
                "landing_page": official_url,
                "official_url": official_url,
                "pdf_url": None,
                "source_provider": "India Code",
                "source_mode": "live",
                "content_hash": content_hash,
                "fetched_at": fetched_at,
                "score": 0.85,
            })
    except Exception as exc:
        logger.warning(f"Error parsing DSpace response: {exc}")
    return results


async def search_india_code(
    query: str,
    max_results: int = 5,
) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    # 1. Check cache first
    cached = get_cached_results(query)
    if cached is not None:
        return [
            {**item, "source_mode": "cached_live"}
            for item in cached[:max_results]
        ]

    # 2. SSRF check
    if not is_safe_url(INDIA_CODE_SEARCH_API):
        logger.error("India Code search URL failed SSRF safety check.")
        return []

    # 3. HTTP Request
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
            resp = await client.get(
                INDIA_CODE_SEARCH_API,
                params={"query": query},
                headers={"User-Agent": "NyayaAI-LegalAssistant/1.0"},
            )
            if resp.status_code != 200:
                logger.warning(f"India Code API returned status code {resp.status_code}")
                return []

            if len(resp.content) > MAX_RESPONSE_BYTES:
                logger.warning("India Code API response exceeded maximum size limit.")
                return []

            data = resp.json()
            parsed_results = parse_dspace_objects(data)
            if parsed_results:
                set_cached_results(query, parsed_results)
            return parsed_results[:max_results]

    except (httpx.TimeoutException, httpx.RequestError, Exception) as exc:
        logger.warning(f"India Code retrieval failed safely: {type(exc).__name__}")
        return []
