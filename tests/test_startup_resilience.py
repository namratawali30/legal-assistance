import pytest

import app.main as main_module


def test_startup_fails_when_database_unavailable(
    client,
    monkeypatch,
):
    calls = {
        "indexes": 0,
        "evidence_indexes": 0,
        "close": 0,
    }

    async def fake_check_database():
        return False

    async def fake_create_indexes():
        calls["indexes"] += 1

    async def fake_evidence_indexes():
        calls["evidence_indexes"] += 1

    async def fake_close_database():
        calls["close"] += 1

    monkeypatch.setattr(
        main_module,
        "check_database_connection",
        fake_check_database,
    )

    monkeypatch.setattr(
        main_module,
        "create_indexes",
        fake_create_indexes,
    )

    monkeypatch.setattr(
        main_module,
        "ensure_evidence_indexes",
        fake_evidence_indexes,
    )

    monkeypatch.setattr(
        main_module,
        "close_database_connection",
        fake_close_database,
    )

    async def exercise():
        async with main_module.lifespan(main_module.app):
            pass

    with pytest.raises(
        RuntimeError,
        match=("Database connection unavailable"),
    ):
        client.portal.call(exercise)

    assert calls["indexes"] == 0
    assert calls["evidence_indexes"] == 0

    assert calls["close"] == 1


def test_startup_fails_when_core_index_creation_fails(
    client,
    monkeypatch,
):
    calls = {
        "evidence_indexes": 0,
        "close": 0,
    }

    async def fake_check_database():
        return True

    async def fake_create_indexes():
        raise RuntimeError("simulated index failure")

    async def fake_evidence_indexes():
        calls["evidence_indexes"] += 1

    async def fake_close_database():
        calls["close"] += 1

    monkeypatch.setattr(
        main_module,
        "check_database_connection",
        fake_check_database,
    )

    monkeypatch.setattr(
        main_module,
        "create_indexes",
        fake_create_indexes,
    )

    monkeypatch.setattr(
        main_module,
        "ensure_evidence_indexes",
        fake_evidence_indexes,
    )

    monkeypatch.setattr(
        main_module,
        "close_database_connection",
        fake_close_database,
    )

    async def exercise():
        async with main_module.lifespan(main_module.app):
            pass

    with pytest.raises(
        RuntimeError,
        match="simulated index failure",
    ):
        client.portal.call(exercise)

    assert calls["evidence_indexes"] == 0

    assert calls["close"] == 1


def test_startup_fails_when_evidence_index_creation_fails(
    client,
    monkeypatch,
):
    calls = {
        "core_indexes": 0,
        "close": 0,
    }

    async def fake_check_database():
        return True

    async def fake_create_indexes():
        calls["core_indexes"] += 1

    async def fake_evidence_indexes():
        raise RuntimeError("simulated evidence index failure")

    async def fake_close_database():
        calls["close"] += 1

    monkeypatch.setattr(
        main_module,
        "check_database_connection",
        fake_check_database,
    )

    monkeypatch.setattr(
        main_module,
        "create_indexes",
        fake_create_indexes,
    )

    monkeypatch.setattr(
        main_module,
        "ensure_evidence_indexes",
        fake_evidence_indexes,
    )

    monkeypatch.setattr(
        main_module,
        "close_database_connection",
        fake_close_database,
    )

    async def exercise():
        async with main_module.lifespan(main_module.app):
            pass

    with pytest.raises(
        RuntimeError,
        match=("simulated evidence " "index failure"),
    ):
        client.portal.call(exercise)

    assert calls["core_indexes"] == 1

    assert calls["close"] == 1


def test_successful_startup_initializes_in_order(
    client,
    monkeypatch,
):
    calls = []

    async def fake_check_database():
        calls.append("database")
        return True

    async def fake_create_indexes():
        calls.append("core_indexes")

    async def fake_evidence_indexes():
        calls.append("evidence_indexes")

    async def fake_close_database():
        calls.append("close")

    monkeypatch.setattr(
        main_module,
        "check_database_connection",
        fake_check_database,
    )

    monkeypatch.setattr(
        main_module,
        "create_indexes",
        fake_create_indexes,
    )

    monkeypatch.setattr(
        main_module,
        "ensure_evidence_indexes",
        fake_evidence_indexes,
    )

    monkeypatch.setattr(
        main_module,
        "close_database_connection",
        fake_close_database,
    )

    async def exercise():
        async with main_module.lifespan(main_module.app):
            calls.append("serving")

    client.portal.call(exercise)

    assert calls == [
        "database",
        "core_indexes",
        "evidence_indexes",
        "serving",
        "close",
    ]
