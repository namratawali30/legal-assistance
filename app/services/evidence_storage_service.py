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

CHUNK_SIZE = 1024 * 1024


class EvidenceStorageError(Exception):
    """Base exception for evidence storage failures."""


class EvidenceTooLargeError(EvidenceStorageError):
    """Raised when an upload exceeds configured size."""


class EvidencePathError(EvidenceStorageError):
    """Raised when a storage path is unsafe."""


class EvidenceWriteError(EvidenceStorageError):
    """Raised when the file cannot be persisted."""


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


def get_max_upload_size_bytes() -> int:
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


def normalize_user_storage_id(
    user_id,
) -> str:
    value = str(user_id).strip()

    # Mongo ObjectIds are hexadecimal, but allowing
    # alphanumeric, underscore and hyphen keeps this
    # helper reusable without permitting path syntax.
    if not re.fullmatch(
        r"[A-Za-z0-9_-]+",
        value,
    ):
        raise EvidencePathError("Invalid evidence storage user identifier.")

    if not value:
        raise EvidencePathError("Invalid evidence storage user identifier.")

    return value


def build_user_evidence_directory(
    user_id,
) -> Path:
    root = get_evidence_root()

    safe_user_id = normalize_user_storage_id(user_id)

    directory = root / safe_user_id

    directory = ensure_path_within_root(
        directory,
        root,
    )

    try:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )
    except OSError as exc:
        raise EvidenceWriteError(
            "Evidence storage directory could not be prepared."
        ) from exc

    return directory


def generate_stored_filename(
    extension: str,
) -> str:
    extension = extension.lower()

    return f"{uuid4().hex}" f"{extension}"


def build_storage_path(
    user_id,
    extension: str,
) -> tuple[Path, str]:
    evidence_root = get_evidence_root()

    user_directory = build_user_evidence_directory(user_id)

    stored_filename = generate_stored_filename(extension)

    final_path = user_directory / stored_filename

    final_path = ensure_path_within_root(
        final_path,
        evidence_root,
    )

    return (
        final_path,
        stored_filename,
    )


def build_relative_storage_path(
    absolute_path: Path,
) -> str:
    evidence_root = get_upload_root()

    safe_path = ensure_path_within_root(
        absolute_path,
        evidence_root,
    )

    relative = safe_path.relative_to(evidence_root)

    return relative.as_posix()


def resolve_storage_path(
    relative_storage_path: str,
) -> Path:
    if not relative_storage_path:
        raise EvidencePathError("Evidence storage path is missing.")

    relative = Path(relative_storage_path)

    if relative.is_absolute():
        raise EvidencePathError("Absolute evidence paths are not allowed.")

    root = get_upload_root()

    candidate = root / relative

    return ensure_path_within_root(
        candidate,
        root,
    )


async def save_evidence_upload(
    upload: UploadFile,
    user_id,
) -> dict:
    original_filename = upload.filename

    (
        extension,
        media_type,
        evidence_type,
    ) = validate_extension_and_media_type(
        filename=original_filename,
        media_type=upload.content_type,
    )

    final_path, stored_filename = build_storage_path(
        user_id=user_id,
        extension=extension,
    )

    user_directory = final_path.parent

    temporary_path = user_directory / (f".{uuid4().hex}" ".upload")

    temporary_path = ensure_path_within_root(
        temporary_path,
        get_evidence_root(),
    )

    maximum_size = get_max_upload_size_bytes()

    size_bytes = 0
    sha256 = hashlib.sha256()

    final_path_created = False
    completed = False

    try:
        try:
            with temporary_path.open("xb") as output:
                while True:
                    chunk = await upload.read(CHUNK_SIZE)

                    if not chunk:
                        break

                    size_bytes += len(chunk)

                    if size_bytes > maximum_size:
                        raise EvidenceTooLargeError(
                            "Evidence file exceeds "
                            "the maximum size of "
                            f"{settings.max_upload_size_mb} MB."
                        )

                    sha256.update(chunk)

                    output.write(chunk)

        except EvidenceTooLargeError:
            raise

        except EvidenceStorageError:
            raise

        except OSError as exc:
            raise EvidenceWriteError(
                "Evidence file could not be written " "to secure storage."
            ) from exc

        except Exception as exc:
            raise EvidenceWriteError(
                "Evidence upload could not be read " "or written securely."
            ) from exc

        if size_bytes == 0:
            raise EvidenceValidationError("Empty evidence files are not allowed.")

        validate_file_signature(
            path=temporary_path,
            extension=extension,
        )

        if final_path.exists():
            raise EvidenceWriteError("Generated evidence filename " "already exists.")

        try:
            os.replace(
                temporary_path,
                final_path,
            )

        except OSError as exc:
            raise EvidenceWriteError(
                "Evidence file could not be finalized " "in secure storage."
            ) from exc

        final_path_created = True

        relative_storage_path = build_relative_storage_path(final_path)

        result = {
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "storage_path": relative_storage_path,
            "evidence_type": evidence_type,
            "media_type": media_type,
            "file_extension": extension,
            "size_bytes": size_bytes,
            "sha256": sha256.hexdigest(),
        }

        completed = True

        return result

    finally:
        # Never leave an incomplete temporary upload.
        if temporary_path.exists():
            try:
                temporary_path.unlink()

            except OSError:
                pass

        # os.replace() may succeed before a later path/
        # metadata-preparation operation fails. In that
        # case the finalized file is still uncommitted
        # and must not become an orphan.
        if final_path_created and not completed:
            try:
                if final_path.exists():
                    final_path.unlink()

            except OSError:
                pass

        # Cleanup of the incoming UploadFile must never
        # mask the real storage result.
        try:
            await upload.close()

        except Exception:
            pass


def delete_stored_evidence_file(
    storage_path: str,
) -> bool:
    path = resolve_storage_path(storage_path)

    if not path.exists():
        return False

    if not path.is_file():
        raise EvidencePathError("Evidence storage target is not a file.")

    try:
        path.unlink()

    except OSError as exc:
        raise EvidenceWriteError("Stored evidence file could not be deleted.") from exc

    return True


def calculate_file_sha256(
    storage_path: str,
) -> str:
    path = resolve_storage_path(storage_path)

    if not path.exists():
        raise EvidenceStorageError("Stored evidence file does not exist.")

    digest = hashlib.sha256()

    try:
        with path.open("rb") as file:
            while True:
                chunk = file.read(CHUNK_SIZE)

                if not chunk:
                    break

                digest.update(chunk)

    except OSError as exc:
        raise EvidenceStorageError("Stored evidence file could not be read.") from exc

    return digest.hexdigest()
