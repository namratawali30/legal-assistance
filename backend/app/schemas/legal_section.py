from pydantic import BaseModel, Field


class LegalSection(BaseModel):
    section_number: str

    section_title: str | None = None

    provision_type: str = "section"

    text: str = Field(
        min_length=1
    )

    page_start: int
    page_end: int


class ParsedLegalDocument(BaseModel):
    source_id: str
    title: str

    act_number: str | None = None

    category: str
    subcategory: str | None = None

    authority: str
    authority_type: str
    document_type: str

    status: str
    effective_from: str | None = None

    landing_page: str
    pdf_url: str

    sections: list[LegalSection]