import logging

logger = logging.getLogger(__name__)


class ProductionConfigError(ValueError):
    """Raised when application configuration is unsafe for production deployment."""
    pass


def validate_production_configuration(settings_obj=None):
    """
    Validates environment and configuration settings against production security criteria.
    Fails fast with sanitized error messages if unsafe settings are detected.
    """
    if settings_obj is None:
        from app.config import settings
        settings_obj = settings

    if settings_obj.environment != "production":
        return

    logger.info("Validating production environment configuration...")

    # 1. JWT Secret Validation
    if not settings_obj.jwt_secret or len(settings_obj.jwt_secret.encode("utf-8")) < 32:
        raise ProductionConfigError("Production configuration requires a secure JWT_SECRET with at least 32 bytes.")

    lowered_secret = settings_obj.jwt_secret.lower()
    insecure_placeholders = (
        "changeme", "change-me", "replace-me", "replace_with", "replace-with",
        "your-secret", "your_secret", "example-secret", "example_secret",
        "development", "dev-secret", "test-secret", "123456"
    )
    if any(p in lowered_secret for p in insecure_placeholders):
        raise ProductionConfigError("Production configuration rejects default or placeholder JWT_SECRET.")

    # 2. LLM API Key Validation
    if not settings_obj.llm_api_key:
        raise ProductionConfigError("Production configuration requires LLM_API_KEY to be set.")

    # 3. CORS Allowed Origins Validation
    origins = getattr(settings_obj, "cors_allowed_origins", [])
    if isinstance(origins, str):
        origins = [o.strip() for o in origins.split(",") if o.strip()]

    if not origins or "*" in origins:
        raise ProductionConfigError("Production configuration requires explicit, non-wildcard CORS_ALLOWED_ORIGINS.")

    # 4. Trusted Hosts Validation
    hosts = getattr(settings_obj, "allowed_hosts", [])
    if isinstance(hosts, str):
        hosts = [h.strip() for h in hosts.split(",") if h.strip()]

    if not hosts or "*" in hosts:
        raise ProductionConfigError("Production configuration requires explicit, non-wildcard ALLOWED_HOSTS.")

    # 5. Storage Backend Validation
    storage_backend = (settings_obj.storage_backend or "local").lower().strip()
    if settings_obj.require_object_storage_in_production and storage_backend == "local":
        raise ProductionConfigError("Production configuration policy forbids local disk evidence storage.")

    if storage_backend == "s3":
        if not settings_obj.object_storage_bucket:
            raise ProductionConfigError("Production object storage requires OBJECT_STORAGE_BUCKET.")
        if not settings_obj.object_storage_access_key or not settings_obj.object_storage_secret_key:
            raise ProductionConfigError("Production object storage requires credentials.")

    # 6. Rate Limiter Multi-Worker Safety
    rate_backend = getattr(settings_obj, "rate_limit_backend", "memory")
    if getattr(settings_obj, "require_shared_rate_limiter_in_production", False) and rate_backend == "memory":
        raise ProductionConfigError("Multi-worker production configuration requires a shared rate limiter backend (e.g., redis).")

    if rate_backend == "redis" and not getattr(settings_obj, "redis_url", None):
        raise ProductionConfigError("Redis rate limiter configuration requires REDIS_URL.")

    # 7. Malware Scanner Production Safety
    scanner_type = getattr(settings_obj, "malware_scanner_type", "mock")
    if getattr(settings_obj, "require_real_malware_scanner_in_production", False) and scanner_type == "mock":
        raise ProductionConfigError("Production configuration forbids mock malware scanner.")

    if scanner_type == "clamav" and not getattr(settings_obj, "clamav_host", None):
        raise ProductionConfigError("ClamAV malware scanner requires CLAMAV_HOST.")

    logger.info("Production environment security validation passed.")
