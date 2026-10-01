from pathlib import Path


ALLOWED_EVIDENCE_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".txt",
    ".docx",
    ".mp3",
    ".wav",
    ".m4a",
    ".mp4",
    ".webm",
}


ALLOWED_MEDIA_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/plain",
    (
        "application/"
        "vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "video/mp4",
    "video/webm",
}


EXTENSION_MEDIA_TYPES = {
    ".pdf": {
        "application/pdf",
    },

    ".jpg": {
        "image/jpeg",
    },

    ".jpeg": {
        "image/jpeg",
    },

    ".png": {
        "image/png",
    },

    ".webp": {
        "image/webp",
    },

    ".txt": {
        "text/plain",
    },

    ".docx": {
        (
            "application/"
            "vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
    },

    ".mp3": {
        "audio/mpeg",
        "audio/mp3",
    },

    ".wav": {
        "audio/wav",
        "audio/x-wav",
    },

    ".m4a": {
        "audio/mp4",
        "audio/m4a",
        "audio/x-m4a",
    },

    ".mp4": {
        "video/mp4",
    },

    ".webm": {
        "video/webm",
    },
}


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".docx",
}


TEXT_EXTENSIONS = {
    ".txt",
}


AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
}


VIDEO_EXTENSIONS = {
    ".mp4",
    ".webm",
}


def normalize_extension(
    filename: str,
) -> str:
    return Path(
        filename
    ).suffix.lower()


def determine_evidence_type(
    extension: str,
) -> str:
    extension = extension.lower()

    if extension in IMAGE_EXTENSIONS:
        return "image"

    if extension in DOCUMENT_EXTENSIONS:
        return "document"

    if extension in TEXT_EXTENSIONS:
        return "text"

    if extension in AUDIO_EXTENSIONS:
        return "audio"

    if extension in VIDEO_EXTENSIONS:
        return "video"

    return "other"


def is_allowed_extension(
    extension: str,
) -> bool:
    return (
        extension.lower()
        in ALLOWED_EVIDENCE_EXTENSIONS
    )


def is_allowed_media_type(
    media_type: str,
) -> bool:
    return (
        media_type
        in ALLOWED_MEDIA_TYPES
    )


def extension_matches_media_type(
    extension: str,
    media_type: str,
) -> bool:
    expected_types = (
        EXTENSION_MEDIA_TYPES.get(
            extension.lower()
        )
    )

    if not expected_types:
        return False

    return (
        media_type
        in expected_types
    )