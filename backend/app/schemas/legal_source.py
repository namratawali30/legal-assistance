from pydantic import BaseModel


class LegalSourceMetadata(BaseModel):
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
    local_path: str

    checksum_sha256: str | None = None
    enabled: bool = True