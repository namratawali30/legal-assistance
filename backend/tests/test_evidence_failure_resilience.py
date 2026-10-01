from bson import ObjectId
import pytest

import app.services.evidence_storage_service as storage
import app.services.evidence_processing_service as processing
import app.services.evidence_service as evidence_service
import app.services.evidence_text_extraction_service as extraction


class FakeUpload:
    def __init__(
        self,
        data=b"Evidence text",
        *,
        read_error=None,
        close_error=None,
    ):
        self.filename = "evidence.txt"
        self.content_type = "text/plain"

        self.data = data
        self.read_error = read_error
        self.close_error = close_error

        self.sent = False
        self.closed = False

    async def read(
        self,
        size,
    ):
        if self.read_error:
            raise self.read_error

        if self.sent:
            return b""

        self.sent = True
        return self.data

    async def close(
        self,
    ):
        self.closed = True

        if self.close_error:
            raise self.close_error


def stored_files(
    root,
):
    if not root.exists():
        return []

    return [path for path in root.rglob("*") if path.is_file()]


# =========================================================
# STORAGE FAILURES
# =========================================================


def test_upload_read_failure_is_normalized_and_cleaned(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = tmp_path / "uploads"

    monkeypatch.setattr(
        storage.settings,
        "upload_dir",
        str(upload_root),
    )

    upload = FakeUpload(read_error=RuntimeError("C:\\private\\raw-upload-error"))

    async def exercise():
        return await storage.save_evidence_upload(
            upload=upload,
            user_id=ObjectId(),
        )

    with pytest.raises(storage.EvidenceWriteError) as exc_info:
        client.portal.call(exercise)

    assert "raw-upload-error" not in str(exc_info.value)

    assert upload.closed is True

    assert stored_files(upload_root) == []


def test_post_replace_failure_does_not_leave_orphan(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = tmp_path / "uploads"

    monkeypatch.setattr(
        storage.settings,
        "upload_dir",
        str(upload_root),
    )

    def fail_relative_path(
        path,
    ):
        raise storage.EvidencePathError("simulated path failure")

    monkeypatch.setattr(
        storage,
        "build_relative_storage_path",
        fail_relative_path,
    )

    upload = FakeUpload()

    async def exercise():
        return await storage.save_evidence_upload(
            upload=upload,
            user_id=ObjectId(),
        )

    with pytest.raises(storage.EvidencePathError):
        client.portal.call(exercise)

    assert upload.closed is True

    assert stored_files(upload_root) == []


def test_upload_close_failure_does_not_mask_success(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = tmp_path / "uploads"

    monkeypatch.setattr(
        storage.settings,
        "upload_dir",
        str(upload_root),
    )

    upload = FakeUpload(close_error=RuntimeError("close failure"))

    async def exercise():
        return await storage.save_evidence_upload(
            upload=upload,
            user_id=ObjectId(),
        )

    result = client.portal.call(exercise)

    assert result["size_bytes"] > 0
    assert upload.closed is True

    assert len(stored_files(upload_root)) == 1


# =========================================================
# PROCESSING FAILURES
# =========================================================


def test_unexpected_extraction_failure_is_safe_and_terminal(
    client,
    monkeypatch,
):
    evidence_id = ObjectId()
    user_id = ObjectId()

    evidence = {
        "_id": evidence_id,
        "user_id": user_id,
        "processing_status": "pending",
    }

    persisted_update = {}

    async def fake_get(
        **kwargs,
    ):
        return evidence

    async def fake_acquire(
        **kwargs,
    ):
        return (
            "lock-token",
            dict(evidence),
        )

    async def fake_finalized_check(
        **kwargs,
    ):
        return None

    async def fake_claim(
        **kwargs,
    ):
        claimed = dict(evidence)
        claimed["processing_status"] = "processing"

        return claimed

    def fail_extraction(
        claimed,
    ):
        raise RuntimeError("C:\\secret\\parser\\failure")

    async def fake_update(
        **kwargs,
    ):
        persisted_update.update(kwargs["update_data"])

        return {
            **evidence,
            **kwargs["update_data"],
        }

    async def fake_release(
        **kwargs,
    ):
        return None

    monkeypatch.setattr(
        processing,
        "get_evidence",
        fake_get,
    )

    monkeypatch.setattr(
        processing,
        "acquire_single_evidence_lock",
        fake_acquire,
    )

    monkeypatch.setattr(
        processing,
        "ensure_evidence_not_finalized_locked",
        fake_finalized_check,
    )

    monkeypatch.setattr(
        processing,
        "claim_evidence_for_processing",
        fake_claim,
    )

    monkeypatch.setattr(
        processing,
        "extract_evidence_text",
        fail_extraction,
    )

    monkeypatch.setattr(
        processing,
        "update_evidence",
        fake_update,
    )

    monkeypatch.setattr(
        processing,
        "release_single_evidence_lock",
        fake_release,
    )

    async def exercise():
        return await processing.process_evidence_for_user(
            evidence_id=evidence_id,
            user_id=user_id,
        )

    result = client.portal.call(exercise)

    assert result["processing_status"] == "failed"

    assert persisted_update["processing_error"] == "Evidence processing failed."

    assert "secret" not in persisted_update["processing_error"]


def test_retry_recovers_stale_processing_state(
    client,
    monkeypatch,
):
    evidence_id = ObjectId()
    user_id = ObjectId()

    evidence = {
        "_id": evidence_id,
        "user_id": user_id,
        "processing_status": "processing",
    }

    allowed_statuses_seen = []

    async def fake_get(
        **kwargs,
    ):
        return evidence

    async def fake_acquire(
        **kwargs,
    ):
        return (
            "lock-token",
            dict(evidence),
        )

    async def fake_finalized_check(
        **kwargs,
    ):
        return None

    async def fake_claim(
        **kwargs,
    ):
        allowed_statuses_seen.extend(kwargs["allowed_statuses"])

        return dict(evidence)

    def fake_extraction(
        claimed,
    ):
        return {
            "processing_status": "ready",
            "extracted_text": "Recovered text",
            "extraction_method": "text",
            "extracted_character_count": 14,
            "extracted_page_count": None,
        }

    async def fake_update(
        **kwargs,
    ):
        return {
            **evidence,
            **kwargs["update_data"],
        }

    async def fail_release(
        **kwargs,
    ):
        # Release failure must not mask success.
        raise RuntimeError("temporary release failure")

    monkeypatch.setattr(
        processing,
        "get_evidence",
        fake_get,
    )

    monkeypatch.setattr(
        processing,
        "acquire_single_evidence_lock",
        fake_acquire,
    )

    monkeypatch.setattr(
        processing,
        "ensure_evidence_not_finalized_locked",
        fake_finalized_check,
    )

    monkeypatch.setattr(
        processing,
        "claim_evidence_for_processing",
        fake_claim,
    )

    monkeypatch.setattr(
        processing,
        "extract_evidence_text",
        fake_extraction,
    )

    monkeypatch.setattr(
        processing,
        "update_evidence",
        fake_update,
    )

    monkeypatch.setattr(
        processing,
        "release_single_evidence_lock",
        fail_release,
    )

    async def exercise():
        return await processing.process_evidence_for_user(
            evidence_id=evidence_id,
            user_id=user_id,
            retry=True,
        )

    result = client.portal.call(exercise)

    assert "processing" in allowed_statuses_seen

    assert result["processing_status"] == "ready"


def test_processing_persistence_exception_is_normalized(
    client,
    monkeypatch,
):
    evidence_id = ObjectId()
    user_id = ObjectId()

    evidence = {
        "_id": evidence_id,
        "user_id": user_id,
        "processing_status": "pending",
    }

    release_called = False

    async def fake_get(
        **kwargs,
    ):
        return evidence

    async def fake_acquire(
        **kwargs,
    ):
        return (
            "lock-token",
            dict(evidence),
        )

    async def fake_finalized_check(
        **kwargs,
    ):
        return None

    async def fake_claim(
        **kwargs,
    ):
        return dict(evidence)

    def fake_extraction(
        claimed,
    ):
        return {
            "processing_status": "no_text",
        }

    async def fail_update(
        **kwargs,
    ):
        raise RuntimeError("mongodb://private-host-details")

    async def fake_release(
        **kwargs,
    ):
        nonlocal release_called

        release_called = True

    monkeypatch.setattr(
        processing,
        "get_evidence",
        fake_get,
    )

    monkeypatch.setattr(
        processing,
        "acquire_single_evidence_lock",
        fake_acquire,
    )

    monkeypatch.setattr(
        processing,
        "ensure_evidence_not_finalized_locked",
        fake_finalized_check,
    )

    monkeypatch.setattr(
        processing,
        "claim_evidence_for_processing",
        fake_claim,
    )

    monkeypatch.setattr(
        processing,
        "extract_evidence_text",
        fake_extraction,
    )

    monkeypatch.setattr(
        processing,
        "update_evidence",
        fail_update,
    )

    monkeypatch.setattr(
        processing,
        "release_single_evidence_lock",
        fake_release,
    )

    async def exercise():
        return await processing.process_evidence_for_user(
            evidence_id=evidence_id,
            user_id=user_id,
        )

    with pytest.raises(processing.EvidenceProcessingPersistenceError) as exc_info:
        client.portal.call(exercise)

    assert "private-host-details" not in str(exc_info.value)

    assert release_called is True


def test_corrupted_pdf_is_normalized(
    tmp_path,
):
    path = tmp_path / "broken.pdf"

    path.write_bytes(b"%PDF-1.7\n" b"not-a-valid-pdf")

    with pytest.raises(extraction.EvidenceExtractionReadError) as exc_info:
        extraction.extract_pdf(path)

    assert "not-a-valid-pdf" not in str(exc_info.value)


def test_corrupted_docx_is_normalized(
    tmp_path,
):
    path = tmp_path / "broken.docx"

    path.write_bytes(b"PK\x03\x04" b"not-a-real-docx-package")

    with pytest.raises(extraction.EvidenceExtractionReadError) as exc_info:
        extraction.extract_docx(path)

    assert "not-a-real-docx-package" not in str(exc_info.value)


def test_integrity_metadata_oserror_is_normalized(
    monkeypatch,
):
    class BrokenPath:
        def exists(
            self,
        ):
            return True

        def is_file(
            self,
        ):
            return True

        def is_symlink(
            self,
        ):
            return False

        def stat(
            self,
        ):
            raise OSError("C:\\private\\filesystem-detail")

    monkeypatch.setattr(
        extraction,
        "resolve_storage_path",
        lambda storage_path: BrokenPath(),
    )

    evidence = {
        "storage_path": "evidence/test.txt",
        "size_bytes": 100,
        "sha256": "a" * 64,
    }

    with pytest.raises(extraction.EvidenceExtractionIntegrityError) as exc_info:
        extraction.verify_evidence_integrity(evidence)

    assert "filesystem-detail" not in str(exc_info.value)
