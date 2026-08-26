from datetime import datetime, timezone
from typing import Any


def build_evidence_document(
    user_id,
    original_filename: str,
    stored_filename: str,
    storage_path: str,
    evidence_type: str,
    media_type: str,
    file_extension: str,
    size_bytes: int,
    sha256: str,
    complaint_id=None,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(
        timezone.utc
    )

    return {
        "user_id":
            user_id,

        "complaint_id":
            complaint_id,

        "title":
            title,

        "description":
            description,

        "original_filename":
            original_filename,

        "stored_filename":
            stored_filename,

        "storage_path":
            storage_path,

        "evidence_type":
            evidence_type,

        "media_type":
            media_type,

        "file_extension":
            file_extension,

        "size_bytes":
            size_bytes,

        "sha256":
            sha256,

        "status":
            "uploaded",

        # ---------------------------------------------
        # PRIVATE PROCESSING STATE
        # ---------------------------------------------

        "processing_status":
            "pending",

        "extraction_method":
            None,

        "extracted_text":
            None,

        "extracted_character_count":
            0,

        "extracted_page_count":
            None,

        "processed_at":
            None,

        "processing_error":
            None,

        "created_at":
            now,

        "updated_at":
            now,
    }