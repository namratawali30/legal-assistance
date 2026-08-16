from datetime import datetime

from pydantic import BaseModel


class EvidenceResponse(BaseModel):
    id: str
    complaint_id: str
    user_id: str
    original_filename: str
    content_type: str
    file_size: int
    storage_path: str
    created_at: datetime