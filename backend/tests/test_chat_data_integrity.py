from copy import deepcopy

from bson import ObjectId

import app.repositories.chat_repository as chat_repository

import app.services.chat_service as chat_service


from app.db.documents import build_message_document



class InsertResult:
    def __init__(
        self,
        inserted_id,
    ):
        self.inserted_id = inserted_id


class UpdateResult:
    matched_count = 1


def test_create_session_does_not_require_post_insert_read(
    client,
    monkeypatch,
):
    session_id = ObjectId()
    user_id = ObjectId()

    async def fake_create(
        session_data,
    ):
        return session_id

    async def unexpected_fetch(
        **kwargs,
    ):
        raise AssertionError(
            "Post-insert fetch should not occur"
        )

    monkeypatch.setattr(
        chat_service,
        "create_chat_session",
        fake_create,
    )

    monkeypatch.setattr(
        chat_service,
        "get_chat_session",
        unexpected_fetch,
    )

    async def exercise():
        return await chat_service.create_session(
            user_id=user_id,
            title="Integrity chat",
            category="consumer_rights",
        )

    result = client.portal.call(
        exercise
    )

    assert result["_id"] == session_id
    assert result["user_id"] == user_id
    assert result["title"] == "Integrity chat"


def test_chat_delete_removes_parent_before_children(
    client,
    monkeypatch,
):
    session_id = ObjectId()
    user_id = ObjectId()

    order = []

    async def fake_get(
        **kwargs,
    ):
        return {
            "_id": session_id,
            "user_id": user_id,
        }

    async def fake_parent_delete(
        **kwargs,
    ):
        order.append("parent")
        return True

    async def fake_child_delete(
        **kwargs,
    ):
        order.append("children")
        assert kwargs[
            "user_id"
        ] == user_id
        return 2

    monkeypatch.setattr(
        chat_service,
        "get_chat_session",
        fake_get,
    )

    monkeypatch.setattr(
        chat_service,
        "delete_chat_session",
        fake_parent_delete,
    )

    monkeypatch.setattr(
        chat_service,
        "delete_session_messages",
        fake_child_delete,
    )

    async def exercise():
        return await chat_service.delete_session(
            session_id=session_id,
            user_id=user_id,
        )

    assert client.portal.call(
        exercise
    ) is True

    assert order == [
        "parent",
        "children",
    ]


def test_parent_delete_failure_preserves_children(
    client,
    monkeypatch,
):
    session_id = ObjectId()
    user_id = ObjectId()

    child_delete_called = False

    async def fake_get(
        **kwargs,
    ):
        return {
            "_id": session_id,
            "user_id": user_id,
        }

    async def fail_parent_delete(
        **kwargs,
    ):
        return False

    async def child_delete(
        **kwargs,
    ):
        nonlocal child_delete_called
        child_delete_called = True
        return 1

    monkeypatch.setattr(
        chat_service,
        "get_chat_session",
        fake_get,
    )

    monkeypatch.setattr(
        chat_service,
        "delete_chat_session",
        fail_parent_delete,
    )

    monkeypatch.setattr(
        chat_service,
        "delete_session_messages",
        child_delete,
    )

    async def exercise():
        return await chat_service.delete_session(
            session_id=session_id,
            user_id=user_id,
        )

    assert client.portal.call(
        exercise
    ) is False

    assert child_delete_called is False


def test_child_cleanup_failure_does_not_reverse_parent_delete(
    client,
    monkeypatch,
):
    session_id = ObjectId()
    user_id = ObjectId()

    async def fake_get(
        **kwargs,
    ):
        return {
            "_id": session_id,
            "user_id": user_id,
        }

    async def parent_delete(
        **kwargs,
    ):
        return True

    async def fail_child_delete(
        **kwargs,
    ):
        raise RuntimeError(
            "simulated child cleanup failure"
        )

    monkeypatch.setattr(
        chat_service,
        "get_chat_session",
        fake_get,
    )

    monkeypatch.setattr(
        chat_service,
        "delete_chat_session",
        parent_delete,
    )

    monkeypatch.setattr(
        chat_service,
        "delete_session_messages",
        fail_child_delete,
    )

    async def exercise():
        return await chat_service.delete_session(
            session_id=session_id,
            user_id=user_id,
        )

    assert client.portal.call(
        exercise
    ) is True


def test_repository_insert_does_not_mutate_message_document(
    client,
    monkeypatch,
):
    inserted_id = ObjectId()

    class FakeCollection:
        async def insert_one(
            self,
            document,
        ):
            # Simulate PyMongo adding _id.
            document["_id"] = inserted_id

            return InsertResult(
                inserted_id
            )

    monkeypatch.setattr(
        chat_repository,
        "messages_collection",
        FakeCollection(),
    )

    original = {
        "session_id": ObjectId(),
        "user_id": ObjectId(),
        "role": "user",
        "content": "Test",
        "sources": [],
    }

    before = deepcopy(
        original
    )

    async def exercise():
        return await (
            chat_repository.create_message(
                original
            )
        )

    assert client.portal.call(
        exercise
    ) == inserted_id

    assert original == before
    assert "_id" not in original


def test_repository_update_does_not_mutate_input_or_identity(
    client,
    monkeypatch,
):
    session_id = ObjectId()
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

    async def fake_get(
        **kwargs,
    ):
        return {
            "_id": session_id,
            "user_id": user_id,
        }

    monkeypatch.setattr(
        chat_repository,
        "chat_sessions_collection",
        FakeCollection(),
    )

    monkeypatch.setattr(
        chat_repository,
        "get_chat_session",
        fake_get,
    )

    supplied = {
        "title": "Updated",
        "_id": ObjectId(),
        "user_id": ObjectId(),
        "created_at": "forged",
    }

    before = deepcopy(
        supplied
    )

    async def exercise():
        return await (
            chat_repository
            .update_chat_session(
                session_id=session_id,
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

    assert persisted[
        "title"
    ] == "Updated"

    assert "_id" not in persisted
    assert "user_id" not in persisted
    assert "created_at" not in persisted
    assert "updated_at" in persisted


def test_get_message_by_id_normalizes_string_ids(
    client,
    monkeypatch,
):
    message_id = ObjectId()
    session_id = ObjectId()
    user_id = ObjectId()

    captured = {}

    class FakeCollection:
        async def find_one(
            self,
            query,
        ):
            captured["query"] = query
            return None

    monkeypatch.setattr(
        chat_repository,
        "messages_collection",
        FakeCollection(),
    )

    async def exercise():
        return await (
            chat_repository
            .get_message_by_id(
                message_id=str(
                    message_id
                ),
                session_id=str(
                    session_id
                ),
                user_id=user_id,
            )
        )

    client.portal.call(
        exercise
    )

    assert captured[
        "query"
    ]["_id"] == message_id

    assert captured[
        "query"
    ]["session_id"] == session_id

    assert captured[
        "query"
    ]["user_id"] == user_id


def test_message_query_is_user_scoped(
    client,
    monkeypatch,
):
    session_id = ObjectId()
    user_id = ObjectId()

    captured = {}

    class FakeCursor:
        def sort(
            self,
            *args,
        ):
            return self

        async def to_list(
            self,
            length,
        ):
            return []

    class FakeCollection:
        def find(
            self,
            query,
        ):
            captured["query"] = query
            return FakeCursor()

    monkeypatch.setattr(
        chat_repository,
        "messages_collection",
        FakeCollection(),
    )

    async def exercise():
        return await (
            chat_repository
            .get_session_messages(
                session_id=str(
                    session_id
                ),
                user_id=user_id,
            )
        )

    client.portal.call(
        exercise
    )

    assert captured[
        "query"
    ] == {
        "session_id":
            session_id,
        "user_id":
            user_id,
    }


def test_message_document_has_consistent_timestamps():
    sources = [
        {
            "citation_id":
                "SOURCE_1"
        }
    ]

    document = build_message_document(
        session_id=ObjectId(),
        user_id=ObjectId(),
        role="assistant",
        content="Test response",
        sources=sources,
    )

    assert (
        document["created_at"]
        == document["updated_at"]
    )

    assert (
        document["created_at"].tzinfo
        is not None
    )

    sources.append(
        {
            "citation_id":
                "SOURCE_2"
        }
    )

    assert len(
        document["sources"]
    ) == 1

    assert document[
        "status"
    ] == "completed"