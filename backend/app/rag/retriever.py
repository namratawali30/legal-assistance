import json
import re
from pathlib import Path
from typing import Any
import math

import faiss
import numpy as np

from app.rag.embeddings import embed_query


BASE_DIR = Path(__file__).resolve().parents[2]

VECTOR_STORE_DIR = (
    BASE_DIR
    / "knowledge_base"
    / "vector_store"
)

INDEX_PATH = (
    VECTOR_STORE_DIR
    / "legal.index"
)

METADATA_PATH = (
    VECTOR_STORE_DIR
    / "legal_metadata.json"
)


_index = None
_metadata = None


def get_index():
    global _index

    if _index is None:
        if not INDEX_PATH.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {INDEX_PATH}"
            )

        _index = faiss.read_index(
            str(INDEX_PATH)
        )

    return _index


def get_metadata() -> list[dict[str, Any]]:
    global _metadata

    if _metadata is None:
        if not METADATA_PATH.exists():
            raise FileNotFoundError(
                f"Legal metadata not found: {METADATA_PATH}"
            )

        with METADATA_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            _metadata = json.load(file)

    return _metadata


def keyword_score(query: str, item: dict[str, Any]) -> float:
    query_tokens = set(re.findall(r"\w+", query.lower()))
    if not query_tokens:
        return 0.0

    text = (
        str(item.get("text", "")) + " " +
        str(item.get("title", "")) + " " +
        str(item.get("provision_title", "")) + " " +
        str(item.get("source_id", ""))
    ).lower()

    matches = 0
    for token in query_tokens:
        if len(token) > 2 and token in text:
            matches += 1

    return matches / len(query_tokens)


def search_legal_chunks(
    query: str,
    top_k: int = 5,
    category: str | None = None,
    use_fusion: bool = True,
) -> list[dict[str, Any]]:

    query = query.strip()

    if not query:
        raise ValueError(
            "Search query cannot be empty"
        )

    if top_k < 1:
        raise ValueError(
            "top_k must be at least 1"
        )

    index = get_index()
    metadata = get_metadata()

    query_embedding = embed_query(
        query
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype="float32",
    ).reshape(1, -1)

    candidate_count = min(
        max(top_k * 10, 50),
        index.ntotal,
    )

    scores, indices = index.search(
        query_embedding,
        candidate_count,
    )

    vector_candidates = []
    for rank, (score, vector_id) in enumerate(zip(scores[0], indices[0])):
        if vector_id < 0 or vector_id >= len(metadata):
            continue
        item = metadata[int(vector_id)].copy()
        if category is not None and item.get("category") != category:
            continue
        item["vector_score"] = float(score)
        item["vector_rank"] = rank
        item["vector_id"] = int(vector_id)
        vector_candidates.append(item)

    if not use_fusion or not vector_candidates:
        results = []
        for item in vector_candidates:
            item["score"] = item["vector_score"]
            results.append(item)
            if len(results) >= top_k:
                break
        return results

    # Candidate Fusion using Reciprocal Rank Fusion (RRF) & Keyword matching
    for item in vector_candidates:
        kw_s = keyword_score(query, item)
        item["keyword_score"] = kw_s
        # RRF formula: 1 / (60 + vector_rank) + keyword_boost
        rrf = (1.0 / (60.0 + item["vector_rank"])) + (kw_s * 0.05)
        item["rrf_score"] = rrf
        # Final normalized score preserving higher-is-better scale
        item["score"] = float(item["vector_score"] + (kw_s * 0.15))

    vector_candidates.sort(key=lambda x: x["rrf_score"], reverse=True)
    return vector_candidates[:top_k]