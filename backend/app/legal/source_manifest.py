import json
from pathlib import Path

from app.schemas.legal_source import LegalSourceMetadata


BASE_DIR = Path(__file__).resolve().parents[2]

MANIFEST_PATH = (
    BASE_DIR
    / "knowledge_base"
    / "manifest"
    / "legal_sources.json"
)


def load_legal_sources() -> list[LegalSourceMetadata]:
    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    return [
        LegalSourceMetadata(**source)
        for source in manifest.get("sources", [])
        if source.get("enabled", True)
    ]