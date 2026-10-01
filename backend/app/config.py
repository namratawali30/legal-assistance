from typing import Literal

from pydantic import (
    Field,
    field_validator,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    app_name: str = Field(
        default="AI Legal Assistance API",
        min_length=1,
        max_length=200,
    )

    app_version: str = Field(
        default="0.1.0",
        min_length=1,
        max_length=50,
    )

    environment: Literal[
        "development",
        "test",
        "production",
    ] = "development"

    # Connection URIs may contain database credentials,
    # so exclude them from Settings.__repr__().
    mongodb_url: str = Field(
        min_length=1,
        max_length=4096,
        repr=False,
    )

    mongodb_database: str = Field(
        min_length=1,
        max_length=200,
    )

    # JWT secrets must never appear in a Settings repr.
    jwt_secret: str = Field(
        min_length=32,
        max_length=512,
        repr=False,
    )

    # Restrict JWT signing to the one algorithm used by
    # this application.
    jwt_algorithm: Literal["HS256"] = "HS256"

    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
    )

    refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        le=90,
    )

    llm_provider: Literal[
        "openrouter",
        "openai",
    ] = "openrouter"

    # Optional in development/test so the backend and
    # deterministic tests can run without a real provider.
    #
    # Production requires this value below.
    llm_api_key: str | None = Field(
        default=None,
        max_length=4096,
        repr=False,
    )

    llm_model: str = Field(
        default="openrouter/free",
        min_length=1,
        max_length=300,
    )

    upload_dir: str = Field(
        default="uploads",
        min_length=1,
        max_length=1024,
    )

    max_upload_size_mb: int = Field(
        default=10,
        ge=1,
        le=100,
    )

    max_audio_upload_size_mb: int = Field(
        default=25,
        ge=1,
        le=200,
    )

    max_video_upload_size_mb: int = Field(
        default=50,
        ge=1,
        le=500,
    )

    cors_allowed_origins: list[str] | str = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
    )

    allowed_hosts: list[str] | str = Field(
        default=["localhost", "127.0.0.1", "testserver"],
    )

    storage_backend: Literal["local", "s3"] = "local"

    object_storage_bucket: str | None = Field(
        default=None,
        max_length=255,
    )

    object_storage_region: str = Field(
        default="us-east-1",
        max_length=100,
    )

    object_storage_endpoint: str | None = Field(
        default=None,
        max_length=1024,
    )

    object_storage_access_key: str | None = Field(
        default=None,
        max_length=512,
        repr=False,
    )

    object_storage_secret_key: str | None = Field(
        default=None,
        max_length=512,
        repr=False,
    )

    object_storage_sse: str | None = Field(
        default="AES256",
        max_length=50,
    )

    require_object_storage_in_production: bool = False

    signed_url_expire_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
    )

    rate_limit_backend: Literal["memory", "redis"] = "memory"
    require_shared_rate_limiter_in_production: bool = False

    malware_scanner_type: Literal["mock", "clamav", "disabled"] = "mock"
    require_real_malware_scanner_in_production: bool = False

    release_id: str = Field(
        default="dev-local",
        max_length=100,
    )

    redis_url: str | None = Field(
        default=None,
        max_length=1024,
        repr=False,
    )

    clamav_host: str = Field(
        default="localhost",
        max_length=255,
    )

    clamav_port: int = Field(
        default=3310,
        ge=1,
        le=65535,
    )

    max_user_evidence_files: int = Field(
        default=50,
        ge=1,
        le=500,
    )

    max_user_storage_mb: int = Field(
        default=250,
        ge=10,
        le=10000,
    )


    # =====================================================
    # NORMALIZATION
    # =====================================================

    @field_validator(
        "environment",
        "llm_provider",
        mode="before",
    )
    @classmethod
    def normalize_identifier(
        cls,
        value,
    ):
        if isinstance(
            value,
            str,
        ):
            return value.strip().lower()

        return value

    @field_validator(
        "app_name",
        "app_version",
        "mongodb_database",
        "llm_model",
        "upload_dir",
        mode="before",
    )
    @classmethod
    def strip_non_secret_strings(
        cls,
        value,
    ):
        if isinstance(
            value,
            str,
        ):
            return value.strip()

        return value

    # =====================================================
    # MONGODB
    # =====================================================

    @field_validator("mongodb_url")
    @classmethod
    def validate_mongodb_url(
        cls,
        value: str,
    ) -> str:
        if value != value.strip():
            raise ValueError(
                "MONGODB_URL must not contain " "leading or trailing whitespace."
            )

        if not value.startswith(
            (
                "mongodb://",
                "mongodb+srv://",
            )
        ):
            raise ValueError("MONGODB_URL must use mongodb:// " "or mongodb+srv://.")

        return value

    # =====================================================
    # JWT SECRET
    # =====================================================

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(
        cls,
        value: str,
    ) -> str:
        if value != value.strip():
            raise ValueError(
                "JWT_SECRET must not contain " "leading or trailing whitespace."
            )

        if len(value.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET must contain at least " "32 UTF-8 bytes.")

        lowered = value.lower()

        obvious_placeholders = (
            "changeme",
            "change-me",
            "replace-me",
            "replace_with",
            "replace-with",
            "your-secret",
            "your_secret",
            "example-secret",
            "example_secret",
        )

        if any(marker in lowered for marker in obvious_placeholders):
            raise ValueError("JWT_SECRET must not use " "a placeholder value.")

        return value

    # =====================================================
    # LLM CREDENTIAL
    # =====================================================

    @field_validator(
        "llm_api_key",
        mode="before",
    )
    @classmethod
    def normalize_llm_api_key(
        cls,
        value,
    ):
        if value is None:
            return None

        if not isinstance(
            value,
            str,
        ):
            return value

        if not value.strip():
            return None

        if value != value.strip():
            raise ValueError(
                "LLM_API_KEY must not contain " "leading or trailing whitespace."
            )

        lowered = value.lower()

        obvious_placeholders = (
            "replace-me",
            "replace_with",
            "replace-with",
            "your-api-key",
            "your_api_key",
            "example-api-key",
        )

        if any(marker in lowered for marker in obvious_placeholders):
            raise ValueError("LLM_API_KEY must not use " "a placeholder value.")

        return value

    # =====================================================
    # PRODUCTION REQUIREMENTS
    # =====================================================

    @model_validator(mode="after")
    def validate_production_settings(
        self,
    ):
        from app.core.production_validator import validate_production_configuration

        if self.environment == "production":
            validate_production_configuration(self)

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
