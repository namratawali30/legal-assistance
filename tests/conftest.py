import os
import uuid

import pytest
from pymongo import MongoClient


# =========================================================
# TEST DATABASE CONFIGURATION
# =========================================================
#
# CRITICAL:
# These environment variables MUST be configured before
# importing app.main, app.config, app.database, or any
# repository.
#
# Several repositories bind their Mongo collection objects
# during module import.
# =========================================================


TEST_DATABASE_PREFIX = (
    "ai_legal_assistance_pytest_"
)


TEST_DATABASE_NAME = (
    TEST_DATABASE_PREFIX
    + uuid.uuid4().hex[:12]
)


os.environ[
    "ENVIRONMENT"
] = "test"

os.environ[
    "MONGODB_DATABASE"
] = TEST_DATABASE_NAME


# These imports MUST remain below the environment setup.

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402


# =========================================================
# DESTRUCTIVE-OPERATION SAFETY GUARD
# =========================================================


def assert_safe_test_database_name(
    database_name: str,
) -> None:
    """
    Refuse destructive cleanup unless the active database
    has the exact pytest-specific prefix generated above.
    """

    if not database_name:
        raise RuntimeError(
            "Refusing test database cleanup: "
            "database name is empty."
        )

    if not database_name.startswith(
        TEST_DATABASE_PREFIX
    ):
        raise RuntimeError(
            "Refusing test database cleanup because "
            "the database name is not pytest-specific: "
            f"{database_name!r}"
        )

    if database_name != TEST_DATABASE_NAME:
        raise RuntimeError(
            "Refusing test database cleanup because "
            "the active database does not match this "
            "pytest session."
        )


def drop_test_database() -> None:
    """
    Drop only this pytest session's isolated database.

    A separate synchronous MongoClient is used here so
    cleanup does not depend on FastAPI's asyncio event loop
    or the application's AsyncMongoClient lifecycle.
    """

    assert_safe_test_database_name(
        settings.mongodb_database
    )

    cleanup_client = MongoClient(
        settings.mongodb_url,
        serverSelectionTimeoutMS=5000,
    )

    try:
        cleanup_client.admin.command(
            "ping"
        )

        cleanup_client.drop_database(
            settings.mongodb_database
        )

    finally:
        cleanup_client.close()


# =========================================================
# FASTAPI TEST CLIENT
# =========================================================


@pytest.fixture(
    scope="session"
)
def client():
    assert (
        settings.environment.lower()
        == "test"
    )

    assert_safe_test_database_name(
        settings.mongodb_database
    )

    # Normally this unique DB cannot already exist,
    # but starting from a known-empty state gives us
    # deterministic tests.
    drop_test_database()

    try:
        with TestClient(
            app
        ) as test_client:
            yield test_client

    finally:
        # TestClient exits first, allowing FastAPI's
        # lifespan/shutdown logic to finish.
        #
        # Then a separate synchronous Mongo client
        # destroys only this pytest session's database.
        drop_test_database()