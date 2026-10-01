import codecs
import zipfile
from pathlib import Path, PurePosixPath

from app.core.evidence_policy import (
    determine_evidence_type,
    extension_matches_media_type,
    is_allowed_extension,
    is_allowed_media_type,
    normalize_extension,
)


class EvidenceValidationError(Exception):
    """Base exception for invalid evidence files."""


class EvidenceFilenameError(
    EvidenceValidationError
):
    """Raised when a filename is unsafe or invalid."""


class EvidenceMediaTypeError(
    EvidenceValidationError
):
    """Raised when extension/MIME validation fails."""


class EvidenceSignatureError(
    EvidenceValidationError
):
    """Raised when file contents do not match the claimed type."""


class EvidenceEmptyFileError(
    EvidenceValidationError
):
    """Raised when an empty file is uploaded."""


def validate_original_filename(
    filename: str | None,
) -> str:
    if filename is None:
        raise EvidenceFilenameError(
            "Evidence filename is required."
        )

    filename = filename.strip()

    if not filename:
        raise EvidenceFilenameError(
            "Evidence filename is required."
        )

    if "\x00" in filename:
        raise EvidenceFilenameError(
            "Evidence filename contains invalid characters."
        )

    # Do not accept directory components supplied by
    # a browser/client.
    if "/" in filename or "\\" in filename:
        raise EvidenceFilenameError(
            "Evidence filename must not contain a path."
        )

    if filename in {
        ".",
        "..",
    }:
        raise EvidenceFilenameError(
            "Invalid evidence filename."
        )

    if len(filename) > 255:
        raise EvidenceFilenameError(
            "Evidence filename is too long."
        )

    extension = normalize_extension(
        filename
    )

    if not extension:
        raise EvidenceFilenameError(
            "Evidence file must have an extension."
        )

    if not is_allowed_extension(
        extension
    ):
        raise EvidenceFilenameError(
            "This evidence file type is not allowed."
        )

    return filename


def normalize_media_type(
    media_type: str | None,
) -> str:
    if not media_type:
        raise EvidenceMediaTypeError(
            "Evidence media type is required."
        )

    # Handles values such as:
    # text/plain; charset=utf-8
    normalized = (
        media_type
        .split(
            ";",
            1,
        )[0]
        .strip()
        .lower()
    )

    if not normalized:
        raise EvidenceMediaTypeError(
            "Evidence media type is required."
        )

    return normalized


def validate_extension_and_media_type(
    filename: str,
    media_type: str | None,
) -> tuple[str, str, str]:
    safe_filename = validate_original_filename(
        filename
    )

    extension = normalize_extension(
        safe_filename
    )

    normalized_media_type = (
        normalize_media_type(
            media_type
        )
    )

    if not is_allowed_media_type(
        normalized_media_type
    ):
        raise EvidenceMediaTypeError(
            "This evidence media type is not allowed."
        )

    if not extension_matches_media_type(
        extension,
        normalized_media_type,
    ):
        raise EvidenceMediaTypeError(
            "Evidence filename extension does not "
            "match its declared media type."
        )

    evidence_type = determine_evidence_type(
        extension
    )

    return (
        extension,
        normalized_media_type,
        evidence_type,
    )


def validate_pdf_signature(
    path: Path,
) -> None:
    with path.open(
        "rb"
    ) as file:
        header = file.read(
            1024
        )

    # PDF header should occur at or very near
    # the beginning of the document.
    if b"%PDF-" not in header:
        raise EvidenceSignatureError(
            "File content is not a valid PDF."
        )


def validate_jpeg_signature(
    path: Path,
) -> None:
    with path.open(
        "rb"
    ) as file:
        header = file.read(
            3
        )

    if not header.startswith(
        b"\xFF\xD8\xFF"
    ):
        raise EvidenceSignatureError(
            "File content is not a valid JPEG image."
        )


def validate_png_signature(
    path: Path,
) -> None:
    with path.open(
        "rb"
    ) as file:
        header = file.read(
            8
        )

    expected = (
        b"\x89PNG\r\n\x1a\n"
    )

    if header != expected:
        raise EvidenceSignatureError(
            "File content is not a valid PNG image."
        )


def validate_webp_signature(
    path: Path,
) -> None:
    with path.open(
        "rb"
    ) as file:
        header = file.read(
            12
        )

    if (
        len(header) < 12
        or header[0:4] != b"RIFF"
        or header[8:12] != b"WEBP"
    ):
        raise EvidenceSignatureError(
            "File content is not a valid WEBP image."
        )


def validate_text_file(
    path: Path,
) -> None:
    decoder = codecs.getincrementaldecoder(
        "utf-8-sig"
    )(
        errors="strict"
    )

    try:
        with path.open(
            "rb"
        ) as file:
            while True:
                chunk = file.read(
                    65536
                )

                if not chunk:
                    break

                # NUL bytes are a strong indication
                # that this is binary rather than
                # ordinary UTF-8 text evidence.
                if b"\x00" in chunk:
                    raise EvidenceSignatureError(
                        "Text evidence contains "
                        "binary data."
                    )

                decoder.decode(
                    chunk,
                    final=False,
                )

        decoder.decode(
            b"",
            final=True,
        )

    except UnicodeDecodeError as exc:
        raise EvidenceSignatureError(
            "Text evidence must be valid UTF-8 text."
        ) from exc


def validate_docx_signature(
    path: Path,
) -> None:
    if not zipfile.is_zipfile(
        path
    ):
        raise EvidenceSignatureError(
            "File content is not a valid DOCX document."
        )

    try:
        with zipfile.ZipFile(
            path,
            "r",
        ) as archive:
            entries = archive.infolist()

            if len(entries) > 5000:
                raise EvidenceSignatureError(
                    "DOCX archive contains too many entries."
                )

            names = {
                entry.filename
                for entry in entries
            }

            required = {
                "[Content_Types].xml",
                "word/document.xml",
            }

            if not required.issubset(
                names
            ):
                raise EvidenceSignatureError(
                    "File does not contain the required "
                    "DOCX document structure."
                )

            total_uncompressed = 0

            for entry in entries:
                total_uncompressed += (
                    entry.file_size
                )

                # DOCX files are never extracted by this
                # service, but reject traversal paths anyway
                # so the stored artifact remains safe for
                # future processing.
                archive_path = PurePosixPath(
                    entry.filename
                )

                if (
                    archive_path.is_absolute()
                    or ".." in archive_path.parts
                ):
                    raise EvidenceSignatureError(
                        "DOCX archive contains unsafe paths."
                    )

                # Standard .docx files should not carry
                # VBA macro projects.
                if (
                    entry.filename
                    .lower()
                    .endswith(
                        "vbaproject.bin"
                    )
                ):
                    raise EvidenceSignatureError(
                        "Macro-enabled Word documents "
                        "are not accepted."
                    )

                if entry.flag_bits & 0x1:
                    raise EvidenceSignatureError(
                        "Encrypted DOCX files are not accepted."
                    )

            # Protect future document processing from
            # extremely compressed ZIP bombs.
            if total_uncompressed > (
                100 * 1024 * 1024
            ):
                raise EvidenceSignatureError(
                    "DOCX expanded content is too large."
                )

    except zipfile.BadZipFile as exc:
        raise EvidenceSignatureError(
            "File content is not a valid DOCX document."
        ) from exc


def validate_mp3_signature(path: Path) -> None:
    with path.open("rb") as file:
        header = file.read(512)
    if header.startswith(b"ID3") or b"\xFF\xFB" in header or b"\xFF\xF3" in header or b"\xFF\xF2" in header:
        return
    raise EvidenceSignatureError("File content is not a valid MP3 audio recording.")


def validate_wav_signature(path: Path) -> None:
    with path.open("rb") as file:
        header = file.read(12)
    if len(header) >= 12 and header[0:4] == b"RIFF" and header[8:12] == b"WAVE":
        return
    raise EvidenceSignatureError("File content is not a valid WAV audio recording.")


def validate_bmff_signature(path: Path) -> None:
    with path.open("rb") as file:
        header = file.read(32)
    if b"ftyp" in header:
        return
    raise EvidenceSignatureError("File content is not a valid MP4/M4A media container.")


def validate_webm_signature(path: Path) -> None:
    with path.open("rb") as file:
        header = file.read(4)
    if header == b"\x1A\x45\xDF\xA3":
        return
    raise EvidenceSignatureError("File content is not a valid WebM media container.")


def validate_file_signature(
    path: Path,
    extension: str,
) -> None:
    if not path.exists():
        raise EvidenceSignatureError(
            "Evidence file could not be found "
            "during validation."
        )

    if path.stat().st_size <= 0:
        raise EvidenceEmptyFileError(
            "Empty evidence files are not allowed."
        )

    extension = extension.lower()

    validators = {
        ".pdf": validate_pdf_signature,
        ".jpg": validate_jpeg_signature,
        ".jpeg": validate_jpeg_signature,
        ".png": validate_png_signature,
        ".webp": validate_webp_signature,
        ".txt": validate_text_file,
        ".docx": validate_docx_signature,
        ".mp3": validate_mp3_signature,
        ".wav": validate_wav_signature,
        ".m4a": validate_bmff_signature,
        ".mp4": validate_bmff_signature,
        ".webm": validate_webm_signature,
    }

    validator = validators.get(extension)

    if validator is None:
        raise EvidenceSignatureError(
            "No validator is available for "
            "this evidence file type."
        )

    validator(path)