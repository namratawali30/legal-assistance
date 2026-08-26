from pathlib import Path
from typing import Any

from app.repositories.evidence_repository import (
    iter_evidence_records_for_reconciliation,
)

from app.services.evidence_storage_service import (
    EvidenceStorageError,
    build_relative_storage_path,
    calculate_file_sha256,
    get_evidence_root,
    get_upload_root,
    normalize_user_storage_id,
    resolve_storage_path,
)


def empty_health_report() -> dict[str, Any]:
    return {
        "records_checked": 0,
        "files_checked": 0,
        "healthy_records": [],
        "missing_files": [],
        "missing_storage_paths": [],
        "unsafe_storage_paths": [],
        "size_mismatches": [],
        "hash_mismatches": [],
        "orphan_files": [],
        "unsafe_filesystem_entries": [],
    }


def evidence_identity(
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "evidence_id": str(evidence.get("_id")),
        "user_id": str(evidence.get("user_id")),
        "complaint_id": (
            str(evidence.get("complaint_id")) if evidence.get("complaint_id") else None
        ),
        "original_filename": evidence.get("original_filename"),
        "storage_path": evidence.get("storage_path"),
    }


def has_health_issues(
    report: dict[str, Any],
) -> bool:
    issue_keys = (
        "missing_files",
        "missing_storage_paths",
        "unsafe_storage_paths",
        "size_mismatches",
        "hash_mismatches",
        "orphan_files",
        "unsafe_filesystem_entries",
    )

    return any(report.get(key) for key in issue_keys)


def get_scan_root(
    user_id=None,
) -> Path:
    evidence_root = get_evidence_root()

    if user_id is None:
        return evidence_root

    safe_user_id = normalize_user_storage_id(user_id)

    candidate = (evidence_root / safe_user_id).resolve(strict=False)

    # The normalized user ID cannot contain path
    # separators, but retain a containment check.
    try:
        candidate.relative_to(evidence_root.resolve())

    except ValueError as exc:
        raise EvidenceStorageError("Unsafe evidence scan path.") from exc

    return candidate


async def build_evidence_health_report(
    user_id=None,
    verify_hashes: bool = True,
) -> dict[str, Any]:
    report = empty_health_report()

    referenced_paths: set[str] = set()

    # =====================================================
    # DATABASE → FILESYSTEM
    # =====================================================

    async for evidence in iter_evidence_records_for_reconciliation(user_id=user_id):
        report["records_checked"] += 1
        record_has_issue = False
        identity = evidence_identity(evidence)
        storage_path = evidence.get("storage_path")

        if not storage_path:
            report["missing_storage_paths"].append(identity)

            continue

        try:
            absolute_path = resolve_storage_path(storage_path)

        except EvidenceStorageError:
            report["unsafe_storage_paths"].append(identity)

            continue

        # Store the canonical relative path only after
        # the storage path has passed containment checks.
        try:
            canonical_relative_path = build_relative_storage_path(absolute_path)

        except EvidenceStorageError:
            report["unsafe_storage_paths"].append(identity)

            continue

        referenced_paths.add(canonical_relative_path)

        if not absolute_path.exists() or not absolute_path.is_file():
            report["missing_files"].append(identity)

            continue

        if absolute_path.is_symlink():
            report["unsafe_storage_paths"].append(identity)

            continue

        try:
            actual_size = absolute_path.stat().st_size

        except OSError:
            report["missing_files"].append(identity)

            continue

        expected_size = evidence.get("size_bytes")

        if expected_size is not None and actual_size != expected_size:
            item = dict(identity)

            item.update(
                {
                    "expected_size": expected_size,
                    "actual_size": actual_size,
                }
            )

            report["size_mismatches"].append(item)
            record_has_issue=True

            # Continue to hash verification as well.
            # A file can legitimately fail both checks.

        if verify_hashes:
            expected_hash = str(evidence.get("sha256", "")).lower()

            try:
                actual_hash = calculate_file_sha256(storage_path)

            except (
                EvidenceStorageError,
                OSError,
            ):
                report["missing_files"].append(identity)

                continue

            if not expected_hash or actual_hash.lower() != expected_hash:
                item = dict(identity)

                item.update(
                    {
                        "expected_sha256": expected_hash,
                        "actual_sha256": actual_hash,
                    }
                )

                report["hash_mismatches"].append(item)
                record_has_issue=True

        # A record is considered healthy only when it
        # appears in none of the database/file mismatch
        # groups above.
        if not record_has_issue:
            report[
                "healthy_records"
            ].append(
                identity
            )

    # =====================================================
    # FILESYSTEM → DATABASE
    # =====================================================

    scan_root = get_scan_root(user_id=user_id)

    if scan_root.exists():
        upload_root = get_upload_root()

        for path in scan_root.rglob("*"):
            if path.is_symlink():
                try:
                    relative = path.relative_to(upload_root).as_posix()

                except ValueError:
                    relative = str(path)

                report["unsafe_filesystem_entries"].append({"storage_path": relative})

                continue

            if not path.is_file():
                continue

            report["files_checked"] += 1

            try:
                relative_path = build_relative_storage_path(path)

            except EvidenceStorageError:
                report["unsafe_filesystem_entries"].append({"storage_path": str(path)})

                continue

            if relative_path not in referenced_paths:
                report["orphan_files"].append(
                    {
                        "storage_path": relative_path,
                        "size_bytes": path.stat().st_size,
                    }
                )

    report["issue_count"] = sum(
        len(report[key])
        for key in (
            "missing_files",
            "missing_storage_paths",
            "unsafe_storage_paths",
            "size_mismatches",
            "hash_mismatches",
            "orphan_files",
            "unsafe_filesystem_entries",
        )
    )

    report["healthy"] = not has_health_issues(report)

    return report
