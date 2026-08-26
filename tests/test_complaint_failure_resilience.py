from bson import ObjectId
import pytest

import app.services.complaint_generation_service as generation

import app.services.complaint_service as complaint_service

import app.services.complaint_export_service as export_service


def test_generation_persistence_failure_is_normalized(
    client,
    monkeypatch,
):
    complaint_id = ObjectId()
    user_id = ObjectId()

    complaint = {
        "_id": complaint_id,
        "user_id": user_id,
        "status": "draft",
        "revision": 0,
        "generated_text": None,
    }

    async def fake_get(
        **kwargs,
    ):
        return complaint

    async def fake_generate(
        **kwargs,
    ):
        return {
            "generated": True,
            "generated_text":
                "Grounded complaint [SOURCE_1]",
            "sources": [],
            "evidence_references": [],
        }

    async def fail_update(
        **kwargs,
    ):
        raise RuntimeError(
            "mongodb://private-host/"
            "sensitive-driver-detail"
        )

    monkeypatch.setattr(
        generation,
        "get_complaint",
        fake_get,
    )

    monkeypatch.setattr(
        generation,
        "generate_grounded_complaint",
        fake_generate,
    )

    monkeypatch.setattr(
        generation,
        "update_complaint_if_unchanged",
        fail_update,
    )

    async def exercise():
        return await (
            generation
            .generate_complaint_for_user(
                complaint_id=complaint_id,
                user_id=user_id,
            )
        )

    with pytest.raises(
        generation
        .ComplaintGenerationPersistenceError
    ) as exc_info:
        client.portal.call(
            exercise
        )

    assert (
        "private-host"
        not in str(exc_info.value)
    )

    assert (
        "sensitive-driver-detail"
        not in str(exc_info.value)
    )


def test_finalization_persistence_failure_is_normalized(
    client,
    monkeypatch,
):
    complaint_id = ObjectId()
    user_id = ObjectId()

    complaint = {
        "_id": complaint_id,
        "user_id": user_id,
        "status": "generated",
        "revision": 3,
        "generated_text": (
            "The applicable legal basis "
            "is cited here. [SOURCE_1]"
        ),
        "sources": [
            {
                "citation_id":
                    "SOURCE_1",
            }
        ],
        "evidence_references": [],
    }

    async def fake_get(
        **kwargs,
    ):
        return complaint

    async def fake_consistency(
        **kwargs,
    ):
        return {
            "consistent": True,
        }

    async def fail_update(
        **kwargs,
    ):
        raise RuntimeError(
            "private MongoDB server details"
        )

    monkeypatch.setattr(
        complaint_service,
        "get_complaint",
        fake_get,
    )

    monkeypatch.setattr(
        complaint_service,
        "validate_complaint_evidence_consistency",
        fake_consistency,
    )

    monkeypatch.setattr(
        complaint_service,
        "update_complaint_if_unchanged",
        fail_update,
    )

    async def exercise():
        return await (
            complaint_service
            .finalize_complaint(
                complaint_id=complaint_id,
                user_id=user_id,
                confirm=True,
            )
        )

    with pytest.raises(
        complaint_service
        .ComplaintPersistenceError
    ) as exc_info:
        client.portal.call(
            exercise
        )

    assert (
        "private MongoDB server details"
        not in str(exc_info.value)
    )


def test_docx_render_failure_is_normalized(
    client,
    monkeypatch,
):
    complaint_id = ObjectId()
    user_id = ObjectId()

    complaint = {
        "_id": complaint_id,
        "status": "finalized",
        "generated_text":
            "Final complaint [SOURCE_1]",
    }

    async def fake_get(
        **kwargs,
    ):
        return complaint

    def fail_build(
        complaint,
    ):
        raise RuntimeError(
            "C:\\private\\docx-library-detail"
        )

    monkeypatch.setattr(
        export_service,
        "get_complaint",
        fake_get,
    )

    monkeypatch.setattr(
        export_service,
        "build_docx_export",
        fail_build,
    )

    async def exercise():
        return await (
            export_service
            .export_complaint_docx(
                complaint_id=complaint_id,
                user_id=user_id,
            )
        )

    with pytest.raises(
        export_service
        .ComplaintExportGenerationError
    ) as exc_info:
        client.portal.call(
            exercise
        )

    assert (
        "docx-library-detail"
        not in str(exc_info.value)
    )


def test_pdf_render_failure_is_normalized(
    client,
    monkeypatch,
):
    complaint_id = ObjectId()
    user_id = ObjectId()

    complaint = {
        "_id": complaint_id,
        "status": "finalized",
        "generated_text":
            "Final complaint [SOURCE_1]",
    }

    async def fake_get(
        **kwargs,
    ):
        return complaint

    def fail_build(
        complaint,
    ):
        raise RuntimeError(
            "private ReportLab internals"
        )

    monkeypatch.setattr(
        export_service,
        "get_complaint",
        fake_get,
    )

    monkeypatch.setattr(
        export_service,
        "build_pdf_export",
        fail_build,
    )

    async def exercise():
        return await (
            export_service
            .export_complaint_pdf(
                complaint_id=complaint_id,
                user_id=user_id,
            )
        )

    with pytest.raises(
        export_service
        .ComplaintExportGenerationError
    ) as exc_info:
        client.portal.call(
            exercise
        )

    assert (
        "ReportLab internals"
        not in str(exc_info.value)
    )


def test_export_database_failure_is_normalized(
    client,
    monkeypatch,
):
    async def fail_get(
        **kwargs,
    ):
        raise RuntimeError(
            "mongodb://secret-host:27017"
        )

    monkeypatch.setattr(
        export_service,
        "get_complaint",
        fail_get,
    )

    async def exercise():
        return await (
            export_service
            .export_complaint_pdf(
                complaint_id=ObjectId(),
                user_id=ObjectId(),
            )
        )

    with pytest.raises(
        export_service
        .ComplaintExportGenerationError
    ) as exc_info:
        client.portal.call(
            exercise
        )

    assert (
        "secret-host"
        not in str(exc_info.value)
    )