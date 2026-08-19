import json
from pathlib import Path
from typing import Any

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


def search_legal_chunks(
    query: str,
    top_k: int = 5,
    category: str | None = None,
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

    # If filtering by category, retrieve extra
    # candidates first and filter afterward.
    candidate_count = (
        min(
            max(top_k * 10, 50),
            index.ntotal,
        )
        if category
        else min(top_k, index.ntotal)
    )

    scores, indices = index.search(
        query_embedding,
        candidate_count,
    )

    results = []

    for score, vector_id in zip(
        scores[0],
        indices[0],
    ):
        if vector_id < 0:
            continue

        if vector_id >= len(metadata):
            continue

        item = metadata[
            int(vector_id)
        ].copy()

        if (
            category is not None
            and item.get("category") != category
        ):
            continue

        item["score"] = float(
            score
        )

        results.append(
            item
        )

        if len(results) >= top_k:
            break

    return results