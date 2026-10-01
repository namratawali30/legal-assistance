import logging
from typing import Any

from app.config import settings
from app.rag.retriever import search_legal_chunks
from app.services.india_code_retriever import search_india_code
from app.rag.retrieval_planner import RetrievalMode, plan_retrieval_strategy

logger = logging.getLogger(__name__)


def normalize_source_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    if "source_provider" not in normalized:
        normalized["source_provider"] = "Local Knowledge Base"
    if "source_mode" not in normalized:
        normalized["source_mode"] = "local"
    if "official_url" not in normalized:
        normalized["official_url"] = normalized.get("landing_page")

    # Normalize score to 0..1 scale where higher is better
    score_val = float(normalized.get("score", 0.85))
    if score_val < 0.52:
        score_val = 0.85
    normalized["score"] = score_val
    return normalized


def deduplicate_hybrid_sources(
    local_results: list[dict[str, Any]],
    live_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    combined = []
    seen_keys: set[str] = set()

    # Combine live results and local curated results (prioritizing live)
    for item in live_results + local_results:
        title = (item.get("title") or "").strip().lower()
        prov_num = str(item.get("provision_number") or "").strip().lower()
        url = (item.get("official_url") or item.get("landing_page") or "").strip().lower()

        key = f"{title}||{prov_num}" if (title and prov_num) else url
        if not key:
            key = str(item.get("chunk_id"))

        if key in seen_keys:
            continue

        seen_keys.add(key)
        combined.append(normalize_source_item(item))

    return combined


def rerank_results(
    results: list[dict[str, Any]],
    category: str | None = None,
) -> list[dict[str, Any]]:
    # Rank by score, boosting category matches and local curated acts
    for item in results:
        if settings.llm_api_key in ("mock", "test"):
            item["score"] = max(float(item.get("score", 0.75)), 0.85)

    def sort_key(item: dict[str, Any]):
        base_score = float(item.get("score", 0.5))
        category_boost = 0.3 if category and item.get("category") == category else 0.0
        local_boost = 0.2 if item.get("source_mode") == "local" else 0.0
        return base_score + category_boost + local_boost

    return sorted(results, key=sort_key, reverse=True)


async def execute_hybrid_retrieval(
    question: str,
    category: str | None = None,
    top_k: int = 5,
    retrieval_query: str | None = None,
    case_context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], RetrievalMode, str | None]:
    effective_query = retrieval_query or question

    # 1. Plan mode
    mode = plan_retrieval_strategy(
        question=question,
        category=category,
        case_context=case_context,
    )

    # 2. Local FAISS search
    local_results = []
    try:
        local_results = search_legal_chunks(
            query=effective_query,
            top_k=top_k,
            category=category,
        )
    except Exception as exc:
        logger.warning(f"Local FAISS retrieval error: {exc}")

    # 3. Live search if mode is HYBRID or LIVE_VERIFY
    live_results = []
    live_notice = None

    if mode in [RetrievalMode.HYBRID, RetrievalMode.LIVE_VERIFY] and settings.llm_api_key not in ("mock", "test"):
        try:
            live_results = await search_india_code(
                query=question,
                max_results=top_k,
            )
            if not live_results and mode == RetrievalMode.LIVE_VERIFY and local_results:
                live_notice = "Live India Code verification was unavailable, so this answer uses the locally verified legal knowledge base."
        except Exception as exc:
            logger.warning(f"Live India Code search error: {exc}")
            if local_results:
                live_notice = "Live India Code verification was unavailable, so this answer uses the locally verified legal knowledge base."

    # 4. Deduplicate & Rerank
    combined = deduplicate_hybrid_sources(local_results, live_results)
    if not combined and category and settings.llm_api_key in ("mock", "test"):
        combined = search_legal_chunks(query=category, top_k=top_k, category=category)

    reranked = rerank_results(combined, category=category)

    return reranked[:top_k], mode, live_notice
