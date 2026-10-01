import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.legal.source_manifest import load_legal_sources


BASE_DIR = Path(__file__).resolve().parents[2]

DOWNLOAD_METADATA_PATH = (
    BASE_DIR
    / "knowledge_base"
    / "manifest"
    / "download_metadata.json"
)


def calculate_sha256(file_path: Path) -> str:
    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            sha256.update(chunk)

    return sha256.hexdigest()


def load_download_metadata() -> dict:
    if not DOWNLOAD_METADATA_PATH.exists():
        return {
            "version": "1.0",
            "downloads": {},
        }

    with DOWNLOAD_METADATA_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_download_metadata(metadata: dict) -> None:
    DOWNLOAD_METADATA_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with DOWNLOAD_METADATA_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
            ensure_ascii=False,
        )


def looks_like_pdf(
    content: bytes,
    content_type: str,
) -> bool:
    if content.startswith(b"%PDF"):
        return True

    return "application/pdf" in content_type.lower()


async def download_source(
    source,
    force: bool = False,
) -> dict:
    destination = BASE_DIR / source.local_path

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata = load_download_metadata()

    existing = metadata["downloads"].get(
        source.source_id
    )

    if (
        destination.exists()
        and existing
        and not force
    ):
        checksum = calculate_sha256(destination)

        return {
            "source_id": source.source_id,
            "status": "already_downloaded",
            "path": str(destination),
            "checksum_sha256": checksum,
        }

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=60.0,
        headers={
            "User-Agent": (
                "AI-Legal-Assistance-Academic-Project/1.0"
            )
        },
    ) as client:
        response = await client.get(
            source.pdf_url
        )

        response.raise_for_status()

    content = response.content

    content_type = response.headers.get(
        "content-type",
        "",
    )

    if not looks_like_pdf(
        content,
        content_type,
    ):
        raise ValueError(
            f"{source.source_id}: "
            "downloaded response is not a PDF"
        )

    destination.write_bytes(content)

    checksum = calculate_sha256(destination)

    now = datetime.now(timezone.utc).isoformat()

    metadata["downloads"][source.source_id] = {
        "source_id": source.source_id,
        "title": source.title,
        "authority": source.authority,
        "source_url": source.pdf_url,
        "local_path": source.local_path,
        "checksum_sha256": checksum,
        "downloaded_at": now,
        "last_verified_at": now,
        "size_bytes": destination.stat().st_size,
    }

    save_download_metadata(metadata)

    return {
        "source_id": source.source_id,
        "status": "downloaded",
        "path": str(destination),
        "checksum_sha256": checksum,
    }


async def download_all_sources(
    force: bool = False,
) -> list[dict]:
    sources = load_legal_sources()

    results = []

    for source in sources:
        try:
            result = await download_source(
                source,
                force=force,
            )

            results.append(result)

        except Exception as exc:
            results.append(
                {
                    "source_id": source.source_id,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    return results