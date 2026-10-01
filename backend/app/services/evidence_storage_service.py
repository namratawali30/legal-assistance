import hashlib
import os
import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import settings
from app.core.evidence_validation import (
    EvidenceValidationError,
    validate_extension_and_media_type,
    validate_file_signature,
)
from app.storage import get_storage_backend
from app.services.malware_scanner import get_malware_scanner, ScanStatus
from app.services.quota_service import check_user_evidence_quota, QuotaExceededError

CHUNK_SIZE = 1024 * 1024


class EvidenceStorageError(Exception):
    """Base exception for evidence storage failures."""
    pass


class EvidenceTooLargeError(EvidenceStorageError):
    """Raised when an upload exceeds configured size."""
    pass


class EvidencePathError(EvidenceStorageError):
    """Raised when a storage path is unsafe."""
    pass


class EvidenceWriteError(EvidenceStorageError):
    """Raised when the file cannot be persisted."""
    pass


class EvidenceInfectedError(EvidenceStorageError):
    """Raised when uploaded file contains malware."""
    pass


def get_backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_upload_root() -> Path:
    configured = Path(settings.upload_dir)
    if configured.is_absolute():
        root = configured
    else:
        root = get_backend_root() / configured
    return root.resolve()


def get_evidence_root() -> Path:
    return (get_upload_root() / "evidence").resolve()


def get_max_upload_size_bytes(evidence_type: str = "document") -> int:
    if evidence_type == "audio":
        return int(settings.max_audio_upload_size_mb * 1024 * 1024)
    if evidence_type == "video":
        return int(settings.max_video_upload_size_mb * 1024 * 1024)
    return int(settings.max_upload_size_mb * 1024 * 1024)


def ensure_path_within_root(
    path: Path,
    root: Path,
) -> Path:
    resolved_root = root.resolve()
    resolved_path = path.resolve(strict=False)
    if not resolved_path.is_relative_to(resolved_root):
        raise EvidencePathError("Unsafe evidence storage path.")
    return resolved_path


def normalize_user_storage_id(user_id) -> str:
    value = str(user_id).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise EvidencePathError("Invalid evidence storage user identifier.")
    if not value:
        raise EvidencePathError("Invalid evidence storage user identifier.")
    return value


def build_user_evidence_directory(user_id) -> Path:
    root = get_evidence_root()
    safe_user_id = normalize_user_storage_id(user_id)
    directory = root / safe_user_id
    directory = ensure_path_within_root(directory, root)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise EvidenceWriteError("Evidence storage directory could not be prepared.") from exc
    return directory


def generate_stored_filename(extension: str) -> str:
    extension = extension.lower()
    return f"{uuid4().hex}{extension}"


def build_storage_path(user_id, extension: str) -> tuple[Path, str]:
    evidence_root = get_evidence_root()
    user_directory = build_user_evidence_directory(user_id)
    stored_filename = generate_stored_filename(extension)
    final_path = user_directory / stored_filename
    final_path = ensure_path_within_root(final_path, evidence_root)
    return final_path, stored_filename


def build_relative_storage_path(absolute_path: Path) -> str:
    evidence_root = get_upload_root()
    safe_path = ensure_path_within_root(absolute_path, evidence_root)
    relative = safe_path.relative_to(evidence_root)
    return relative.as_posix()


def resolve_storage_path(relative_storage_path: str) -> Path:
    if not relative_storage_path:
        raise EvidencePathError("Evidence storage path is missing.")
    relative = Path(relative_storage_path)
    if relative.is_absolute():
        raise EvidencePathError("Absolute evidence paths are not allowed.")
    root = get_upload_root()
    candidate = root / relative
    return ensure_path_within_root(candidate, root)


async def save_evidence_upload(
    upload: UploadFile,
    user_id,
) -> dict:
    original_filename = upload.filename or "file.bin"
    safe_user_id = normalize_user_storage_id(user_id)

    (
        extension,
        media_type,
        evidence_type,
    ) = validate_extension_and_media_type(
        filename=original_filename,
        media_type=upload.content_type,
    )

    maximum_size = get_max_upload_size_bytes(evidence_type)

    content_chunks = []
    size_bytes = 0
    sha256 = hashlib.sha256()

    completed = False
    stored_path_to_clean = None

    try:
        try:
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break
                size_bytes += len(chunk)
                if size_bytes > maximum_size:
                    raise EvidenceTooLargeError(
                        f"Evidence file exceeds maximum allowed size for {evidence_type}."
                    )
                sha256.update(chunk)
                content_chunks.append(chunk)

        except EvidenceTooLargeError:
            raise
        except EvidenceStorageError:
            raise
        except Exception as exc:
            raise EvidenceWriteError("Evidence upload could not be read or written securely.") from exc

        if size_bytes == 0:
            raise EvidenceValidationError("Empty evidence files are not allowed.")

        full_content = b"".join(content_chunks)

        # Quota check
        await check_user_evidence_quota(user_id, new_file_size_bytes=size_bytes)

        # Malware scan
        scanner = get_malware_scanner()
        scan_status = await scanner.scan_bytes(full_content, original_filename)
        if scan_status == ScanStatus.INFECTED:
            raise EvidenceInfectedError("Upload rejected: File failed security scan (malware detected).")
        if scan_status == ScanStatus.SCAN_FAILED:
            raise EvidenceStorageError("Upload rejected: Malware scanner service failure.")

        # Signature validation using a temp file
        temp_dir = get_upload_root() / "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = temp_dir / f".tmp_{uuid4().hex}"
        try:
            with open(temp_file, "wb") as f:
                f.write(full_content)
            validate_file_signature(path=temp_file, extension=extension)
        finally:
            if temp_file.exists():
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

        # Build paths (this will invoke build_relative_storage_path which tests might monkeypatch)
        final_path, stored_filename = build_storage_path(user_id=user_id, extension=extension)
        relative_storage_path = build_relative_storage_path(final_path)

        storage_backend = get_storage_backend()
        stored_path_to_clean = relative_storage_path

        await storage_backend.put(
            key=relative_storage_path,
            data=full_content,
            content_type=media_type,
        )

        completed = True
        return {
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "storage_path": relative_storage_path,
            "evidence_type": evidence_type,
            "media_type": media_type,
            "file_extension": extension,
            "size_bytes": size_bytes,
            "sha256": sha256.hexdigest(),
            "scan_status": scan_status.value if isinstance(scan_status, ScanStatus) else str(scan_status),
        }

    finally:
        if not completed and stored_path_to_clean:
            try:
                delete_stored_evidence_file(stored_path_to_clean)
            except Exception:
                pass

        try:
            await upload.close()
        except Exception:
            pass


async def delete_stored_evidence_file_async(storage_path: str) -> bool:
    storage_backend = get_storage_backend()
    if await storage_backend.exists(storage_path):
        return await storage_backend.delete(storage_path)
    return False


def delete_stored_evidence_file(storage_path: str) -> bool:
    try:
        path = resolve_storage_path(storage_path)
        if path.exists() and path.is_file():
            path.unlink()
            return True
    except Exception:
        pass

    storage_backend = get_storage_backend()
    if hasattr(storage_backend, "root_path"):
        try:
            path = storage_backend._resolve_key(storage_path)
            if path.exists():
                path.unlink()
                return True
        except Exception:
            pass
    return False


async def get_evidence_file_bytes(storage_path: str) -> bytes:
    storage_backend = get_storage_backend()
    return await storage_backend.get(storage_path)


async def calculate_file_sha256_async(storage_path: str) -> str:
    content = await get_evidence_file_bytes(storage_path)
    return hashlib.sha256(content).hexdigest()


def calculate_file_sha256(storage_path: str) -> str:
    path = resolve_storage_path(storage_path)
    if not path.exists():
        raise EvidenceStorageError("Stored evidence file does not exist.")
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
