import json
from pathlib import Path

import faiss
import numpy as np

from app.rag.embeddings import embed_texts


BASE_DIR = Path(__file__).resolve().parents[2]

CHUNKS_PATH = (
    BASE_DIR
    / "knowledge_base"
    / "chunks"
    / "legal_chunks.json"
)

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


def load_chunks() -> list[dict]:
    with CHUNKS_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def build_faiss_index() -> dict:
    chunks = load_chunks()

    if not chunks:
        raise ValueError(
            "No legal chunks found"
        )

    texts = [
        chunk["embedding_text"]
        for chunk in chunks
    ]

    embeddings = embed_texts(
        texts
    )

    embeddings = np.asarray(
        embeddings,
        dtype="float32",
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(
        embeddings
    )

    VECTOR_STORE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    faiss.write_index(
        index,
        str(INDEX_PATH),
    )

    metadata = []

    for vector_id, chunk in enumerate(
        chunks
    ):
        metadata.append(
            {
                "vector_id": vector_id,
                "chunk_id": chunk["chunk_id"],
                "source_id": chunk["source_id"],
                "title": chunk["title"],
                "category": chunk["category"],
                "subcategory": chunk.get(
                    "subcategory"
                ),
                "authority": chunk["authority"],
                "document_type": chunk[
                    "document_type"
                ],
                "provision_type": chunk[
                    "provision_type"
                ],
                "provision_number": chunk[
                    "provision_number"
                ],
                "provision_title": chunk.get(
                    "provision_title"
                ),
                "page_start": chunk[
                    "page_start"
                ],
                "page_end": chunk[
                    "page_end"
                ],
                "landing_page": chunk.get(
                    "landing_page"
                ),
                "pdf_url": chunk.get(
                    "pdf_url"
                ),
                "text": chunk["text"],
            }
        )

    with METADATA_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return {
        "vectors": index.ntotal,
        "dimension": dimension,
        "index_path": str(
            INDEX_PATH
        ),
        "metadata_path": str(
            METADATA_PATH
        ),
    }