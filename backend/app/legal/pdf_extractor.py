import json
from pathlib import Path

import pymupdf

from app.legal.source_manifest import load_legal_sources


BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = (
    BASE_DIR
    / "knowledge_base"
    / "processed"
)


def clean_page_text(text: str) -> str:
    lines = [
        line.strip()
        for line in text.splitlines()
    ]

    cleaned_lines = [
        line
        for line in lines
        if line
    ]

    return "\n".join(cleaned_lines)


def extract_pdf_pages(
    pdf_path: Path,
) -> list[dict]:
    document = pymupdf.open(pdf_path)

    pages = []

    try:
        for page_index in range(len(document)):
            page = document[page_index]

            text = page.get_text(
                "text",
                sort=True,
            )

            cleaned_text = clean_page_text(text)

            pages.append(
                {
                    "page_number": page_index + 1,
                    "text": cleaned_text,
                }
            )

    finally:
        document.close()

    return pages


def extract_source(source) -> dict:
    pdf_path = BASE_DIR / source.local_path

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    pages = extract_pdf_pages(pdf_path)

    return {
        "source_id": source.source_id,
        "title": source.title,
        "act_number": source.act_number,
        "category": source.category,
        "subcategory": source.subcategory,
        "authority": source.authority,
        "authority_type": source.authority_type,
        "document_type": source.document_type,
        "status": source.status,
        "effective_from": source.effective_from,
        "landing_page": source.landing_page,
        "pdf_url": source.pdf_url,
        "pages": pages,
    }


def save_extracted_source(
    source,
    extracted: dict,
) -> Path:
    output_dir = (
        PROCESSED_DIR
        / source.category
    )

    if source.subcategory:
        output_dir = (
            output_dir
            / source.subcategory
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / f"{source.source_id}.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            extracted,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_path


def extract_all_sources() -> list[dict]:
    sources = load_legal_sources()

    results = []

    for source in sources:
        try:
            extracted = extract_source(source)

            output_path = save_extracted_source(
                source,
                extracted,
            )

            results.append(
                {
                    "source_id": source.source_id,
                    "status": "extracted",
                    "pages": len(
                        extracted["pages"]
                    ),
                    "output": str(output_path),
                }
            )

        except Exception as exc:
            results.append(
                {
                    "source_id": source.source_id,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    return results