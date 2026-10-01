import json
import re
from pathlib import Path
from typing import Any

from app.legal.source_manifest import load_legal_sources
from app.schemas.legal_section import (
    LegalSection,
    ParsedLegalDocument,
)


BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = (
    BASE_DIR
    / "knowledge_base"
    / "processed"
)

PARSED_DIR = (
    BASE_DIR
    / "knowledge_base"
    / "parsed"
)


ACT_SECTION_PATTERN = re.compile(
    r"^\s*(\d+[A-Z]?)\.\s+(.+?)\s*$"
)


SUMMARY_PATTERN = re.compile(
    r"^\s*(\d+)\.\s*([A-Z][A-Z\s\-]+):\s*(.*)$"
)


AMENDMENT_MAIN_PATTERN = re.compile(
    r"^\s*(\d+)\.\s+(.+)$"
)


AMENDMENT_PARA_PATTERN = re.compile(
    r"^\s*(\d+\([a-z]\))\.\s*(.*)$",
    re.IGNORECASE,
)


def normalize_whitespace(
    text: str,
) -> str:
    text = text.replace(
        "\u00a0",
        " ",
    )

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


def looks_like_act_section(
    line: str,
) -> tuple[str, str] | None:
    line = normalize_whitespace(
        line
    )

    match = ACT_SECTION_PATTERN.match(
        line
    )

    if not match:
        return None

    number = match.group(1)
    heading = match.group(2).strip()

    if len(heading) < 2:
        return None

    if len(heading) > 250:
        return None

    return number, heading


def load_extracted_document(
    source,
) -> dict[str, Any]:
    path = (
        PROCESSED_DIR
        / source.category
    )

    if source.subcategory:
        path = (
            path
            / source.subcategory
        )

    path = (
        path
        / f"{source.source_id}.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Extracted document not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def parse_act_sections(
    extracted_document: dict[str, Any],
) -> list[LegalSection]:
    sections: list[LegalSection] = []

    current_number: str | None = None
    current_title: str | None = None
    current_lines: list[str] = []

    current_page_start: int | None = None
    current_page_end: int | None = None

    def save_current():
        nonlocal current_number
        nonlocal current_title
        nonlocal current_lines
        nonlocal current_page_start
        nonlocal current_page_end

        if current_number is None:
            return

        text = normalize_whitespace(
            "\n".join(
                current_lines
            )
        )

        if text:
            sections.append(
                LegalSection(
                    section_number=current_number,
                    section_title=current_title,
                    provision_type="section",
                    text=text,
                    page_start=(
                        current_page_start
                        or 1
                    ),
                    page_end=(
                        current_page_end
                        or current_page_start
                        or 1
                    ),
                )
            )

        current_number = None
        current_title = None
        current_lines = []
        current_page_start = None
        current_page_end = None

    for page in extracted_document.get(
        "pages",
        [],
    ):
        page_number = page.get(
            "page_number",
            1,
        )

        lines = page.get(
            "text",
            "",
        ).splitlines()

        for raw_line in lines:
            line = raw_line.strip()

            if not line:
                continue

            detected = looks_like_act_section(
                line
            )

            if detected:
                save_current()

                number, title = detected

                current_number = number
                current_title = title

                current_page_start = page_number
                current_page_end = page_number

                current_lines = [
                    f"{number}. {title}"
                ]

                continue

            if current_number is not None:
                current_lines.append(
                    line
                )

                current_page_end = (
                    page_number
                )

    save_current()

    return sections


def deduplicate_act_sections(
    sections: list[LegalSection],
) -> list[LegalSection]:
    latest_by_number = {}

    for section in sections:
        latest_by_number[
            section.section_number
        ] = section

    def sort_key(
        section: LegalSection,
    ):
        match = re.match(
            r"^(\d+)([A-Z]?)$",
            section.section_number,
        )

        if not match:
            return (
                999999,
                section.section_number,
            )

        return (
            int(match.group(1)),
            match.group(2),
        )

    return sorted(
        latest_by_number.values(),
        key=sort_key,
    )


def parse_ugc_summary(
    extracted_document: dict[str, Any],
) -> list[LegalSection]:
    provisions: list[LegalSection] = []

    current_number: str | None = None
    current_title: str | None = None
    current_lines: list[str] = []

    current_page_start: int | None = None
    current_page_end: int | None = None

    def save_current():
        nonlocal current_number
        nonlocal current_title
        nonlocal current_lines
        nonlocal current_page_start
        nonlocal current_page_end

        if current_number is None:
            return

        text = normalize_whitespace(
            "\n".join(
                current_lines
            )
        )

        if text:
            provisions.append(
                LegalSection(
                    section_number=current_number,
                    section_title=current_title,
                    provision_type="summary_provision",
                    text=text,
                    page_start=(
                        current_page_start
                        or 1
                    ),
                    page_end=(
                        current_page_end
                        or current_page_start
                        or 1
                    ),
                )
            )

        current_number = None
        current_title = None
        current_lines = []
        current_page_start = None
        current_page_end = None

    for page in extracted_document.get(
        "pages",
        [],
    ):
        page_number = page.get(
            "page_number",
            1,
        )

        for raw_line in page.get(
            "text",
            "",
        ).splitlines():

            line = normalize_whitespace(
                raw_line
            )

            if not line:
                continue

            match = SUMMARY_PATTERN.match(
                line
            )

            if match:
                save_current()

                current_number = (
                    match.group(1)
                )

                current_title = (
                    match.group(2)
                    .strip()
                    .title()
                )

                remainder = (
                    match.group(3)
                    .strip()
                )

                current_page_start = (
                    page_number
                )

                current_page_end = (
                    page_number
                )

                current_lines = [
                    (
                        f"{current_number}. "
                        f"{current_title}"
                    )
                ]

                if remainder:
                    current_lines.append(
                        remainder
                    )

                continue

            if current_number is not None:
                current_lines.append(
                    line
                )

                current_page_end = (
                    page_number
                )

    save_current()

    return provisions


def parse_ugc_amendment(
    extracted_document: dict[str, Any],
) -> list[LegalSection]:
    provisions: list[LegalSection] = []

    usable_pages = []

    for page in extracted_document.get(
        "pages",
        [],
    ):
        text = page.get(
            "text",
            "",
        )

        english_score = sum(
            char.isascii()
            and char.isalpha()
            for char in text
        )

        if english_score >= 100:
            usable_pages.append(
                page
            )

    combined_lines: list[
        tuple[int, str]
    ] = []

    for page in usable_pages:
        page_number = page.get(
            "page_number",
            1,
        )

        for raw_line in page.get(
            "text",
            "",
        ).splitlines():

            line = normalize_whitespace(
                raw_line
            )

            if line:
                combined_lines.append(
                    (
                        page_number,
                        line,
                    )
                )

    current_number: str | None = None
    current_title: str | None = None
    current_lines: list[str] = []

    current_page_start: int | None = None
    current_page_end: int | None = None

    def save_current():
        nonlocal current_number
        nonlocal current_title
        nonlocal current_lines
        nonlocal current_page_start
        nonlocal current_page_end

        if current_number is None:
            return

        text = normalize_whitespace(
            "\n".join(
                current_lines
            )
        )

        if text:
            provisions.append(
                LegalSection(
                    section_number=current_number,
                    section_title=current_title,
                    provision_type="amendment",
                    text=text,
                    page_start=(
                        current_page_start
                        or 1
                    ),
                    page_end=(
                        current_page_end
                        or current_page_start
                        or 1
                    ),
                )
            )

        current_number = None
        current_title = None
        current_lines = []
        current_page_start = None
        current_page_end = None

    for page_number, line in combined_lines:

        paragraph_match = (
            AMENDMENT_PARA_PATTERN
            .match(line)
        )

        main_match = (
            AMENDMENT_MAIN_PATTERN
            .match(line)
        )

        if paragraph_match:
            save_current()

            current_number = (
                paragraph_match
                .group(1)
            )

            current_title = (
                "Amendment provision"
            )

            current_page_start = (
                page_number
            )

            current_page_end = (
                page_number
            )

            current_lines = [
                line
            ]

            continue

        if main_match:
            number = (
                main_match
                .group(1)
            )

            heading = (
                main_match
                .group(2)
                .strip()
            )

            # Avoid treating Gazette page numbers
            # or very short fragments as provisions.
            if (
                len(heading) >= 10
                and len(heading) <= 500
            ):
                save_current()

                current_number = (
                    number
                )

                current_title = (
                    "Amendment provision"
                )

                current_page_start = (
                    page_number
                )

                current_page_end = (
                    page_number
                )

                current_lines = [
                    f"{number}. {heading}"
                ]

                continue

        if current_number is not None:
            current_lines.append(
                line
            )

            current_page_end = (
                page_number
            )

    save_current()

    return provisions


def parse_source(
    source,
) -> ParsedLegalDocument:
    extracted = load_extracted_document(
        source
    )

    if (
        source.document_type
        == "regulation_summary"
    ):
        sections = parse_ugc_summary(
            extracted
        )

    elif (
        source.document_type
        == "regulation_amendment"
    ):
        sections = parse_ugc_amendment(
            extracted
        )

    else:
        raw_sections = parse_act_sections(
            extracted
        )

        sections = deduplicate_act_sections(
            raw_sections
        )

    return ParsedLegalDocument(
        source_id=source.source_id,
        title=source.title,
        act_number=source.act_number,
        category=source.category,
        subcategory=source.subcategory,
        authority=source.authority,
        authority_type=source.authority_type,
        document_type=source.document_type,
        status=source.status,
        effective_from=source.effective_from,
        landing_page=source.landing_page,
        pdf_url=source.pdf_url,
        sections=sections,
    )


def save_parsed_document(
    document: ParsedLegalDocument,
) -> Path:
    output_dir = (
        PARSED_DIR
        / document.category
    )

    if document.subcategory:
        output_dir = (
            output_dir
            / document.subcategory
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / f"{document.source_id}.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            document.model_dump(),
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_path


def parse_all_sources() -> list[dict[str, Any]]:
    sources = load_legal_sources()

    results = []

    for source in sources:
        try:
            document = parse_source(
                source
            )

            output_path = (
                save_parsed_document(
                    document
                )
            )

            results.append(
                {
                    "source_id":
                        source.source_id,
                    "status":
                        "parsed",
                    "sections":
                        len(
                            document.sections
                        ),
                    "output":
                        str(output_path),
                }
            )

        except Exception as exc:
            results.append(
                {
                    "source_id":
                        source.source_id,
                    "status":
                        "failed",
                    "error":
                        str(exc),
                }
            )

    return results