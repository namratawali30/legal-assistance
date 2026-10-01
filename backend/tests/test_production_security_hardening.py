import asyncio
import io
import pytest
from fastapi import HTTPException
from app.config import Settings
from app.core.production_validator import (
    validate_production_configuration,
    ProductionConfigError,
)
from app.storage.base import StorageError, StorageNotFoundError
from app.storage.local_storage import LocalStorageBackend
from app.storage.s3_storage import S3StorageBackend
from app.storage import get_storage_backend, reset_storage_backend
from app.services.malware_scanner import MockMalwareScanner, ScanStatus
from app.services.quota_service import check_user_evidence_quota, QuotaExceededError
from app.services.rate_limiter import InMemoryRateLimiterBackend, RateLimitExceeded, RateLimiter
from app.rag.evidence_context import build_evidence_context


# ====================================================================
# A. PRODUCTION PLACEHOLDER JWT SECRET
# ====================================================================
def test_production_placeholder_jwt_secret_rejected():
    with pytest.raises(Exception, match="JWT_SECRET must not use a placeholder value"):
        Settings(
            environment="production",
            jwt_secret="changeme_changeme_changeme_changeme_1234",
            llm_api_key="valid-llm-key",
            cors_allowed_origins=["https://app.nyaya.ai"],
            allowed_hosts=["app.nyaya.ai"],
            storage_backend="s3",
            object_storage_bucket="private-bucket",
            object_storage_access_key="key",
            object_storage_secret_key="secret",
        )


# ====================================================================
# B. PRODUCTION MISSING JWT SECRET / WEAK JWT SECRET
# ====================================================================
def test_production_weak_jwt_secret_rejected():
    with pytest.raises(Exception, match="at least 32 characters"):
        Settings(
            environment="production",
            jwt_secret="short",
            llm_api_key="valid-key",
        )


# ====================================================================
# C. TEST/DEV MODE ALLOWS LOCAL STORAGE
# ====================================================================
def test_dev_mode_allows_local_storage():
    reset_storage_backend()
    s = Settings(
        environment="development",
        jwt_secret="a_very_long_valid_jwt_secret_string_32bytes_long",
        storage_backend="local",
    )
    validate_production_configuration(s)  # should not raise for development
    backend = get_storage_backend()
    assert isinstance(backend, LocalStorageBackend)
    reset_storage_backend()


# ====================================================================
# D. WILDCARD PRODUCTION CORS & TRUSTED HOSTS
# ====================================================================
def test_wildcard_production_cors_rejected():
    with pytest.raises(Exception, match="explicit, non-wildcard CORS_ALLOWED_ORIGINS"):
        Settings(
            environment="production",
            jwt_secret="a_very_long_valid_jwt_secret_string_32bytes_long",
            llm_api_key="valid-llm-key",
            cors_allowed_origins=["*"],
            allowed_hosts=["app.nyaya.ai"],
            storage_backend="s3",
            object_storage_bucket="private-bucket",
            object_storage_access_key="key",
            object_storage_secret_key="secret",
        )


def test_wildcard_production_trusted_hosts_rejected():
    with pytest.raises(Exception, match="explicit, non-wildcard ALLOWED_HOSTS"):
        Settings(
            environment="production",
            jwt_secret="a_very_long_valid_jwt_secret_string_32bytes_long",
            llm_api_key="valid-llm-key",
            cors_allowed_origins=["https://nyaya.ai"],
            allowed_hosts=["*"],
            storage_backend="s3",
            object_storage_bucket="private-bucket",
            object_storage_access_key="key",
            object_storage_secret_key="secret",
        )


# ====================================================================
# E. EXPLICIT PRODUCTION ORIGIN
# ====================================================================
def test_explicit_production_origin_accepted():
    s = Settings(
        environment="production",
        jwt_secret="a_very_long_valid_jwt_secret_string_32bytes_long",
        llm_api_key="valid-llm-key",
        cors_allowed_origins=["https://nyaya.ai", "https://app.nyaya.ai"],
        allowed_hosts=["nyaya.ai", "app.nyaya.ai"],
        storage_backend="s3",
        object_storage_bucket="private-bucket",
        object_storage_access_key="key",
        object_storage_secret_key="secret",
    )
    validate_production_configuration(s)  # Should pass without error


# ====================================================================
# F. INVALID STORAGE BACKEND
# ====================================================================
def test_invalid_storage_backend_rejected():
    reset_storage_backend()
    from app.config import settings
    original_backend = settings.storage_backend
    settings.storage_backend = "invalid_backend"
    with pytest.raises(ValueError, match="Unsupported STORAGE_BACKEND"):
        get_storage_backend()
    settings.storage_backend = original_backend
    reset_storage_backend()


# ====================================================================
# G. PRODUCTION LOCAL STORAGE
# ====================================================================
def test_production_local_storage_rejected_when_object_storage_required():
    with pytest.raises(Exception, match="forbids local disk evidence storage"):
        Settings(
            environment="production",
            jwt_secret="a_very_long_valid_jwt_secret_string_32bytes_long",
            llm_api_key="valid-llm-key",
            cors_allowed_origins=["https://nyaya.ai"],
            allowed_hosts=["nyaya.ai"],
            storage_backend="local",
            require_object_storage_in_production=True,
        )


# ====================================================================
# MULTI-WORKER RATE LIMITER SAFETY & MOCK SCANNER REJECTION
# ====================================================================
def test_multi_worker_rate_limiter_production_rejection():
    with pytest.raises(Exception, match="requires a shared rate limiter backend"):
        Settings(
            environment="production",
            jwt_secret="a_very_long_valid_jwt_secret_string_32bytes_long",
            llm_api_key="valid-llm-key",
            cors_allowed_origins=["https://nyaya.ai"],
            allowed_hosts=["nyaya.ai"],
            rate_limit_backend="memory",
            require_shared_rate_limiter_in_production=True,
        )


def test_mock_malware_scanner_production_rejection():
    with pytest.raises(Exception, match="forbids mock malware scanner"):
        Settings(
            environment="production",
            jwt_secret="a_very_long_valid_jwt_secret_string_32bytes_long",
            llm_api_key="valid-llm-key",
            cors_allowed_origins=["https://nyaya.ai"],
            allowed_hosts=["nyaya.ai"],
            malware_scanner_type="mock",
            require_real_malware_scanner_in_production=True,
        )


# ====================================================================
# H. PRIVATE OBJECT STORAGE DRIVER PUT & GET
# ====================================================================
@pytest.mark.anyio
async def test_local_storage_put_get_delete(tmp_path):
    backend = LocalStorageBackend(root_dir=tmp_path)
    key = "users/user123/evidence/file123/original.txt"
    stored_key = await backend.put(key, b"hello secret content", "text/plain")
    assert stored_key == key
    assert await backend.exists(key) is True
    data = await backend.get(key)
    assert data == b"hello secret content"
    deleted = await backend.delete(key)
    assert deleted is True
    assert await backend.exists(key) is False


# ====================================================================
# J. UNSAFE OBJECT KEY PREVENTED
# ====================================================================
@pytest.mark.anyio
async def test_unsafe_object_key_path_traversal(tmp_path):
    backend = LocalStorageBackend(root_dir=tmp_path)
    unsafe_key = "../../../etc/passwd"
    with pytest.raises(StorageError, match="Unsafe storage path traversal"):
        await backend.put(unsafe_key, b"data")


# ====================================================================
# Q. RATE LIMIT EXCEEDED
# ====================================================================
@pytest.mark.anyio
async def test_rate_limiter_sliding_window():
    limiter = RateLimiter(backend=InMemoryRateLimiterBackend())
    ip_key = "test_client_ip_123"

    for _ in range(5):
        await limiter.check_rate_limit(ip_key, max_requests=5, window_seconds=60, force=True)

    with pytest.raises(RateLimitExceeded) as exc_info:
        await limiter.check_rate_limit(ip_key, max_requests=5, window_seconds=60, force=True)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


# ====================================================================
# S & T & U & V. MALWARE SCANNER & QUARANTINE GATING TEST SUITE
# ====================================================================
@pytest.mark.anyio
async def test_malware_scanner_clean():
    scanner = MockMalwareScanner()
    res = await scanner.scan_bytes(b"Normal clean contract document content", "contract.txt")
    assert res == ScanStatus.CLEAN


@pytest.mark.anyio
async def test_malware_scanner_infected():
    scanner = MockMalwareScanner()
    res = await scanner.scan_bytes(b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE", "virus.txt")
    assert res == ScanStatus.INFECTED


@pytest.mark.anyio
async def test_malware_scanner_failure():
    scanner = MockMalwareScanner()
    res = await scanner.scan_bytes(b"SIMULATE_SCANNER_FAILURE", "broken.txt")
    assert res == ScanStatus.SCAN_FAILED


def test_quarantine_downstream_gating():
    records = [
        {
            "_id": "clean_1",
            "title": "Clean Invoice",
            "extracted_text": "Invoice paid INR 10,000",
            "processing_status": "ready",
            "scan_status": "CLEAN",
        },
        {
            "_id": "infected_2",
            "title": "Malicious PDF",
            "extracted_text": "Infected text",
            "processing_status": "ready",
            "scan_status": "INFECTED",
        },
        {
            "_id": "scan_failed_3",
            "title": "Failed Scan PDF",
            "extracted_text": "Text in unverified doc",
            "processing_status": "ready",
            "scan_status": "SCAN_FAILED",
        },
    ]

    context_res = build_evidence_context(records)
    assert context_res["included_count"] == 1
    assert context_res["references"][0]["evidence_id"] == "clean_1"
