from bson import ObjectId

import app.db.indexes as indexes
import app.repositories.complaint_repository as complaint_repository

import app.repositories.evidence_repository as evidence_repository



class RecordingCollection:
    def __init__(self):
        self.index_calls = []

    async def create_index(
        self,
        keys,
        **kwargs,
    ):
        self.index_calls.append(
            (
                keys,
                kwargs,
            )
        )

        return kwargs.get(
            "name",
            "generated_index",
        )


class FakeDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(
        self,
        name,
    ):
        if name not in self.collections:
            self.collections[
                name
            ] = RecordingCollection()

        return self.collections[
            name
        ]


def has_index(
    calls,
    expected_keys,
    **expected_options,
):
    return any(
        keys == expected_keys
        and all(
            options.get(
                option_name
            )
            == option_value
            for (
                option_name,
                option_value,
            ) in expected_options.items()
        )
        for keys, options in calls
    )


def test_core_index_contracts(
    client,
    monkeypatch,
):
    fake_database = FakeDatabase()

    monkeypatch.setattr(
        indexes,
        "database",
        fake_database,
    )

    async def exercise():
        await indexes.create_indexes()

    client.portal.call(
        exercise
    )

    users = fake_database.collections[
        indexes.USERS_COLLECTION
    ]

    chats = fake_database.collections[
        indexes.CHAT_SESSIONS_COLLECTION
    ]

    messages = fake_database.collections[
        indexes.MESSAGES_COLLECTION
    ]

    complaints = fake_database.collections[
        indexes.COMPLAINTS_COLLECTION
    ]

    assert has_index(
        users.index_calls,
        "email",
        unique=True,
    )

    assert has_index(
        chats.index_calls,
        [
            (
                "user_id",
                1,
            ),
            (
                "updated_at",
                -1,
            ),
        ],
    )

    assert has_index(
        messages.index_calls,
        [
            (
                "session_id",
                1,
            ),
            (
                "created_at",
                1,
            ),
        ],
    )

    assert has_index(
        complaints.index_calls,
        [
            (
                "user_id",
                1,
            ),
            (
                "updated_at",
                -1,
            ),
        ],
    )

    assert has_index(
        complaints.index_calls,
        [
            (
                "user_id",
                1,
            ),
            (
                "status",
                1,
            ),
            (
                "evidence_references.evidence_id",
                1,
            ),
        ],
    )


def test_evidence_index_contracts(
    client,
    monkeypatch,
):
    collection = RecordingCollection()

    monkeypatch.setattr(
        evidence_repository,
        "evidence_collection",
        collection,
    )

    async def exercise():
        await (
            evidence_repository
            .ensure_evidence_indexes()
        )

    client.portal.call(
        exercise
    )

    assert has_index(
        collection.index_calls,
        [
            (
                "user_id",
                1,
            ),
            (
                "complaint_id",
                1,
            ),
            (
                "sha256",
                1,
            ),
        ],
        unique=True,
        name=(
            evidence_repository
            .EVIDENCE_UNIQUE_SCOPE_INDEX
        ),
    )

    assert has_index(
        collection.index_calls,
        [
            (
                "user_id",
                1,
            ),
            (
                "created_at",
                -1,
            ),
        ],
        name="evidence_user_created",
    )

    assert has_index(
        collection.index_calls,
        [
            (
                "user_id",
                1,
            ),
            (
                "complaint_id",
                1,
            ),
            (
                "created_at",
                -1,
            ),
        ],
        name=(
            "evidence_user_complaint_created"
        ),
    )


def test_finalized_evidence_lookup_uses_string_reference(
    client,
    monkeypatch,
):
    evidence_id = ObjectId()
    user_id = ObjectId()

    captured = {}

    class FakeComplaintCollection:
        async def find_one(
            self,
            query,
        ):
            captured[
                "query"
            ] = query

            return None

    monkeypatch.setattr(
        complaint_repository,
        "complaints_collection",
        FakeComplaintCollection(),
    )

    async def exercise():
        return await (
            complaint_repository
            .get_finalized_complaint_citing_evidence(
                evidence_id=evidence_id,
                user_id=user_id,
            )
        )

    result = client.portal.call(
        exercise
    )

    assert result is None

    assert captured[
        "query"
    ] == {
        "user_id": user_id,
        "status": "finalized",
        "evidence_references": {
            "$elemMatch": {
                "evidence_id":
                    str(evidence_id),
            }
        },
    }