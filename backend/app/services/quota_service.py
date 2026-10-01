from app.config import settings
from app.repositories.evidence_repository import evidence_collection


class QuotaExceededError(Exception):
    """Raised when a user resource quota is exceeded."""
    pass


async def check_user_evidence_quota(user_id: str, new_file_size_bytes: int = 0):
    """
    Validates user evidence file count and total storage bytes against configured limits.
    """
    max_files = getattr(settings, "max_user_evidence_files", 50)
    max_total_mb = getattr(settings, "max_user_storage_mb", 250)
    max_total_bytes = max_total_mb * 1024 * 1024

    cursor = evidence_collection.find({"user_id": str(user_id)})
    existing_docs = await cursor.to_list(length=1000)

    current_file_count = len(existing_docs)
    if current_file_count >= max_files:
        raise QuotaExceededError(
            f"User evidence file limit of {max_files} files has been reached."
        )

    current_total_bytes = sum(int(doc.get("file_size_bytes", 0)) for doc in existing_docs)
    if current_total_bytes + new_file_size_bytes > max_total_bytes:
        raise QuotaExceededError(
            f"User total storage quota of {max_total_mb} MB would be exceeded."
        )
