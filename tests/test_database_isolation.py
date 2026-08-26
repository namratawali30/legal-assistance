from app.config import settings
from app.database import (
    database,
)


def test_pytest_uses_isolated_database():
    assert (
        settings.environment.lower()
        == "test"
    )

    assert (
        settings.mongodb_database.startswith(
            "ai_legal_assistance_pytest_"
        )
    )

    assert (
        database.name
        == settings.mongodb_database
    )


def test_pytest_database_name_is_not_generic():
    dangerous_names = {
        "legal_assistance",
        "legal_assistant",
        "development",
        "production",
        "prod",
        "test",
    }

    assert (
        settings.mongodb_database.lower()
        not in dangerous_names
    )

    assert len(
        settings.mongodb_database
    ) > len(
        "ai_legal_assistance_pytest_"
    )