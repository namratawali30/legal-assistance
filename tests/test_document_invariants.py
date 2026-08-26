from copy import deepcopy
from datetime import (
    date,
    datetime,
    timezone,
)

from bson import ObjectId

import app.repositories.complaint_repository as complaint_repository

import app.repositories.evidence_repository as evidence_repository


from app.db.complaint_documents import build_complaint_document

from app.db.evidence_documents import build_evidence_document

class InsertResult:
    def __init__(
        self,
        inserted_id,
    ):
        self.inserted_id = inserted_id


class UpdateResult:
    matched_count = 1


def test_complaint_document_has_complete_draft_state():
    user_id = ObjectId()

    document = build_complaint_document(
        user_id=user_id,
        title="Consumer complaint",
        category="consumer_rights",
        complainant_name="Test User",
        respondent_name="Test Seller",
        facts="A defective product was supplied.",
    )

    assert document["user_id"] == user_id
    assert document["status"] == "draft"

    assert document["generated_text"] is None
    assert document["sources"] == []
    assert document["evidence_references"] == []

    assert document["generated_at"] is None
    assert document["finalized_at"] is None

    assert (
        document["created_at"]
        == document["updated_at"]
    )

    assert (
        document["created_at"].tzinfo
        is not None
    )


def test_complaint_additional_details_are_copied():
    details = {
        "invoice": {
            "number": "INV-123",
        }
    }

    document = build_complaint_document(
        user_id=ObjectId(),
        title="Consumer complaint",
        category="consumer_rights",
        complainant_name="Test User",
        respondent_name="Test Seller",
        facts="Test facts",
        additional_details=details,
    )

    details[
        "invoice"
    ][
        "number"
    ] = "MUTATED"

    assert (
        document[
            "additional_details"
        ][
            "invoice"
        ][
            "number"
        ]
        == "INV-123"
    )


def test_complaint_incident_date_is_normalized():
    document = build_complaint_document(
        user_id=ObjectId(),
        title="Complaint",
        category="consumer_rights",
        complainant_name="User",
        respondent_name="Seller",
        facts="Facts",
        incident_date=date(
            2026,
            8,
            25,
        ),
    )

    assert (
        document["incident_date"]
        == "2026-08-25"
    )


def test_evidence_document_has_complete_initial_state():
    user_id = ObjectId()

    document = build_evidence_document(
        user_id=user_id,
        complaint_id=None,
        original_filename="invoice.pdf",
        stored_filename="stored.pdf",
        storage_path="user/stored.pdf",
        evidence_type="document",
        media_type="application/pdf",
        file_extension=".pdf",
        size_bytes=1234,
        sha256="a" * 64,
    )

    assert document["user_id"] == user_id
    assert document["complaint_id"] is None

    assert document["status"] == "uploaded"
    assert (
        document["processing_status"]
        == "pending"
    )

    assert document["extracted_text"] is None
    assert document["extraction_method"] is None

    assert (
        document["extracted_character_count"]
        == 0
    )

    assert document["extracted_page_count"] is None
    assert document["processed_at"] is None
    assert document["processing_error"] is None

    assert (
        document["created_at"]
        == document["updated_at"]
    )

    assert (
        document["created_at"].tzinfo
        is not None
    )


def test_create_evidence_does_not_mutate_input(
    client,
    monkeypatch,
):
    inserted_id = ObjectId()

    class FakeCollection:
        async def insert_one(
            self,
            document,
        ):
            # Simulate PyMongo attaching _id.
            document["_id"] = inserted_id

            return InsertResult(
                inserted_id
            )

    monkeypatch.setattr(
        evidence_repository,
        "evidence_collection",
        FakeCollection(),
    )

    supplied = {
        "user_id": ObjectId(),
        "sha256": "a" * 64,
    }

    before = deepcopy(
        supplied
    )

    async def exercise():
        return await (
            evidence_repository
            .create_evidence(
                supplied
            )
        )

    result = client.portal.call(
        exercise
    )

    assert result == inserted_id
    assert supplied == before
    assert "_id" not in supplied


def test_evidence_update_protects_storage_identity(
    client,
    monkeypatch,
):
    evidence_id = ObjectId()
    user_id = ObjectId()

    captured = {}

    class FakeCollection:
        async def update_one(
            self,
            query,
            update,
        ):
            captured["query"] = query
            captured["update"] = update

            return UpdateResult()

        async def find_one(
            self,
            query,
        ):
            return {
                "_id": evidence_id,
                "user_id": user_id,
            }

    monkeypatch.setattr(
        evidence_repository,
        "evidence_collection",
        FakeCollection(),
    )

    supplied = {
        "title": "Updated title",
        "_id": ObjectId(),
        "user_id": ObjectId(),
        "complaint_id": ObjectId(),
        "storage_path": "forged/path",
        "sha256": "b" * 64,
        "created_at": datetime.now(
            timezone.utc
        ),
    }

    before = deepcopy(
        supplied
    )

    async def exercise():
        return await (
            evidence_repository
            .update_evidence(
                evidence_id=evidence_id,
                user_id=user_id,
                update_data=supplied,
            )
        )

    client.portal.call(
        exercise
    )

    assert supplied == before

    persisted = captured[
        "update"
    ]["$set"]

    assert (
        persisted["title"]
        == "Updated title"
    )

    assert "_id" not in persisted
    assert "user_id" not in persisted
    assert "complaint_id" not in persisted
    assert "storage_path" not in persisted
    assert "sha256" not in persisted
    assert "created_at" not in persisted

    assert "updated_at" in persisted


def test_complaint_update_protects_repository_identity(
    client,
    monkeypatch,
):
    complaint_id = ObjectId()
    user_id = ObjectId()

    captured = {}

    class FakeCollection:
        async def find_one_and_update(
            self,
            query,
            update,
            return_document,
        ):
            captured["query"] = query
            captured["update"] = update

            return {
                "_id": complaint_id,
                "user_id": user_id,
            }

    monkeypatch.setattr(
        complaint_repository,
        "complaints_collection",
        FakeCollection(),
    )

    supplied = {
        "title": "Updated complaint",
        "_id": ObjectId(),
        "user_id": ObjectId(),
        "created_at": datetime.now(
            timezone.utc
        ),
        "revision": 999,
    }

    before = deepcopy(
        supplied
    )

    async def exercise():
        return await (
            complaint_repository
            .update_complaint(
                complaint_id=complaint_id,
                user_id=user_id,
                update_data=supplied,
            )
        )

    client.portal.call(
        exercise
    )

    assert supplied == before

    persisted = captured[
        "update"
    ]["$set"]

    assert (
        persisted["title"]
        == "Updated complaint"
    )

    assert "_id" not in persisted
    assert "user_id" not in persisted
    assert "created_at" not in persisted
    assert "revision" not in persisted

    assert "updated_at" in persisted

    assert captured[
        "update"
    ][
        "$inc"
    ][
        "revision"
    ] == 1