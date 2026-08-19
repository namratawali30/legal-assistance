import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]

PARSED_DIR = (
    BASE_DIR
    / "knowledge_base"
    / "parsed"
)

CHUNKS_DIR = (
    BASE_DIR
    / "knowledge_base"
    / "chunks"
)


MAX_CHUNK_CHARS = 2500
CHUNK_OVERLAP_CHARS = 250


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ")

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def split_long_text(
    text: str,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap: int = CHUNK_OVERLAP_CHARS,
) -> list[str]:

    text = normalize_text(text)

    if len(text) <= max_chars:
        return [text]

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(
            start + max_chars,
            text_length,
        )

        if end < text_length:
            break_positions = [
                text.rfind(
                    "\n",
                    start,
                    end,
                ),
                text.rfind(
                    ". ",
                    start,
                    end,
                ),
                text.rfind(
                    "; ",
                    start,
                    end,
                ),
            ]

            best_break = max(
                break_positions
            )

            if best_break > start + 500:
                end = best_break + 1

        chunk = text[
            start:end
        ].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = max(
            end - overlap,
            start + 1,
        )

        start = next_start

    return chunks


def build_chunk_text(
    document: dict[str, Any],
    provision: dict[str, Any],
    body: str,
) -> str:

    title = document.get(
        "title",
        ""
    )

    number = provision.get(
        "section_number",
        ""
    )

    provision_title = provision.get(
        "section_title"
    )

    provision_type = provision.get(
        "provision_type",
        "section",
    )

    lines = [
        f"Legal Source: {title}",
        f"Provision Type: {provision_type}",
        f"Provision Number: {number}",
    ]

    if provision_title:
        lines.append(
            f"Provision Title: {provision_title}"
        )

    lines.append("")

    lines.append(body)

    return "\n".join(lines)


def build_document_chunks(
    document: dict[str, Any],
) -> list[dict[str, Any]]:

    chunks = []

    source_id = document["source_id"]

    for provision in document.get(
        "sections",
        [],
    ):
        provision_number = str(
            provision.get(
                "section_number",
                ""
            )
        )

        body_parts = split_long_text(
            provision["text"]
        )

        total_parts = len(
            body_parts
        )

        for part_index, body in enumerate(
            body_parts,
            start=1,
        ):
            chunk_id = (
                f"{source_id}"
                f"__{provision_number}"
                f"__{part_index}"
            )

            chunk_text = build_chunk_text(
                document,
                provision,
                body,
            )

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "source_id": source_id,

                    "title": document.get(
                        "title"
                    ),

                    "act_number": document.get(
                        "act_number"
                    ),

                    "category": document.get(
                        "category"
                    ),

                    "subcategory": document.get(
                        "subcategory"
                    ),

                    "authority": document.get(
                        "authority"
                    ),

                    "authority_type": document.get(
                        "authority_type"
                    ),

                    "document_type": document.get(
                        "document_type"
                    ),

                    "status": document.get(
                        "status"
                    ),

                    "effective_from": document.get(
                        "effective_from"
                    ),

                    "landing_page": document.get(
                        "landing_page"
                    ),

                    "pdf_url": document.get(
                        "pdf_url"
                    ),

                    "provision_type": provision.get(
                        "provision_type",
                        "section",
                    ),

                    "provision_number":
                        provision_number,

                    "provision_title":
                        provision.get(
                            "section_title"
                        ),

                    "page_start":
                        provision.get(
                            "page_start"
                        ),

                    "page_end":
                        provision.get(
                            "page_end"
                        ),

                    "part": part_index,
                    "total_parts": total_parts,

                    "text": body,

                    "embedding_text":
                        chunk_text,
                }
            )

    return chunks


def load_parsed_documents():
    documents = []

    for path in PARSED_DIR.rglob(
        "*.json"
    ):
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            documents.append(
                json.load(file)
            )

    return documents


def build_all_chunks() -> list[dict[str, Any]]:
    documents = load_parsed_documents()

    chunks = []

    for document in documents:
        chunks.extend(
            build_document_chunks(
                document
            )
        )

    return chunks


def save_chunks(
    chunks: list[dict[str, Any]],
) -> Path:

    CHUNKS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        CHUNKS_DIR
        / "legal_chunks.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            chunks,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_path