import pytest

from pydantic import (
    ValidationError,
)

from app.config import Settings


VALID_JWT_SECRET = (
    "J"
    * 48
)


def valid_settings(
    **overrides,
):
    values = {
        "environment":
            "test",

        "mongodb_url":
            "mongodb://localhost:27017",

        "mongodb_database":
            "legal_test",

        "jwt_secret":
            VALID_JWT_SECRET,

        "llm_provider":
            "openrouter",

        "llm_api_key":
            None,

        "llm_model":
            "openrouter/free",

        "access_token_expire_minutes":
            30,

        "upload_dir":
            "uploads",

        "max_upload_size_mb":
            10,
    }

    values.update(
        overrides
    )

    return Settings(
        _env_file=None,
        **values,
    )


# =========================================================
# SECRET VALIDATION
# =========================================================


def test_valid_settings_load():
    settings = valid_settings()

    assert (
        settings.environment
        == "test"
    )

    assert (
        settings.jwt_algorithm
        == "HS256"
    )


def test_short_jwt_secret_rejected():
    with pytest.raises(
        ValidationError
    ):
        valid_settings(
            jwt_secret="too-short"
        )


def test_placeholder_jwt_secret_rejected():
    with pytest.raises(
        ValidationError
    ):
        valid_settings(
            jwt_secret=(
                "replace-me-with-a-real-secret-"
                "that-is-long-enough"
            )
        )


def test_jwt_secret_surrounding_whitespace_rejected():
    with pytest.raises(
        ValidationError
    ):
        valid_settings(
            jwt_secret=(
                " "
                + VALID_JWT_SECRET
                + " "
            )
        )


def test_sensitive_values_not_in_settings_repr():
    mongo_url = (
        "mongodb://"
        "test-user:"
        "super-secret-password"
        "@localhost:27017"
    )

    llm_key = (
        "provider-secret-key"
    )

    settings = valid_settings(
        mongodb_url=mongo_url,
        llm_api_key=llm_key,
    )

    rendered = repr(
        settings
    )

    assert (
        "super-secret-password"
        not in rendered
    )

    assert (
        VALID_JWT_SECRET
        not in rendered
    )

    assert (
        llm_key
        not in rendered
    )


# =========================================================
# ENUM / CONFIG RESTRICTIONS
# =========================================================


def test_invalid_environment_rejected():
    with pytest.raises(
        ValidationError
    ):
        valid_settings(
            environment="staging-ish"
        )


def test_environment_is_normalized():
    settings = valid_settings(
        environment=" TEST "
    )

    assert (
        settings.environment
        == "test"
    )


def test_invalid_llm_provider_rejected():
    with pytest.raises(
        ValidationError
    ):
        valid_settings(
            llm_provider=(
                "arbitrary-provider"
            )
        )


def test_llm_provider_is_normalized():
    settings = valid_settings(
        llm_provider=" OPENROUTER "
    )

    assert (
        settings.llm_provider
        == "openrouter"
    )


def test_non_hs256_algorithm_rejected():
    with pytest.raises(
        ValidationError
    ):
        valid_settings(
            jwt_algorithm="none"
        )


# =========================================================
# DATABASE CONFIG
# =========================================================


def test_invalid_mongodb_scheme_rejected():
    with pytest.raises(
        ValidationError
    ):
        valid_settings(
            mongodb_url=(
                "http://localhost:27017"
            )
        )


def test_blank_database_name_rejected():
    with pytest.raises(
        ValidationError
    ):
        valid_settings(
            mongodb_database="   "
        )


# =========================================================
# NUMERIC SAFETY BOUNDS
# =========================================================


@pytest.mark.parametrize(
    "minutes",
    [
        0,
        1441,
    ],
)
def test_token_expiry_bounds(
    minutes,
):
    with pytest.raises(
        ValidationError
    ):
        valid_settings(
            access_token_expire_minutes=(
                minutes
            )
        )


@pytest.mark.parametrize(
    "size_mb",
    [
        0,
        101,
    ],
)
def test_upload_size_bounds(
    size_mb,
):
    with pytest.raises(
        ValidationError
    ):
        valid_settings(
            max_upload_size_mb=size_mb
        )


# =========================================================
# LLM KEY POLICY
# =========================================================


def test_development_can_load_without_llm_key():
    settings = valid_settings(
        environment="development",
        llm_api_key=None,
    )

    assert (
        settings.llm_api_key
        is None
    )


def test_blank_llm_key_normalizes_to_none():
    settings = valid_settings(
        llm_api_key="   "
    )

    assert (
        settings.llm_api_key
        is None
    )


def test_production_requires_llm_key():
    with pytest.raises(
        ValidationError
    ):
        valid_settings(
            environment="production",
            llm_api_key=None,
        )


def test_production_accepts_configured_llm_key():
    settings = valid_settings(
        environment="production",
        llm_api_key=(
            "configured-production-key"
        ),
    )

    assert (
        settings.environment
        == "production"
    )


def test_placeholder_llm_key_rejected():
    with pytest.raises(
        ValidationError
    ):
        valid_settings(
            llm_api_key=(
                "your-api-key-goes-here"
            )
        )