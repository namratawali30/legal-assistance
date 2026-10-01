import json
import logging
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings, Settings
from app.core.logging_config import StructuredJSONFormatter, request_id_ctx
from app.services.rate_limiter import RedisRateLimiterBackend, RateLimitExceeded
from app.services.malware_scanner import ClamAVMalwareScanner, ScanStatus
from app.core.production_validator import validate_production_configuration, ProductionConfigError


client = TestClient(app)


# ====================================================================
# 1. SYSTEM ENDPOINTS (/health, /version, /readiness)
# ====================================================================
def test_health_endpoint_minimal():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_endpoint_exposes_safe_metadata():
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "release_id" in data
    assert "environment" in data
    # Ensure zero secrets leaked in version response
    assert "jwt_secret" not in data
    assert "mongodb_url" not in data


def test_system_readiness_probe():
    response = client.get("/readiness")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "checks" in data


# ====================================================================
# 2. X-REQUEST-ID CORRELATION HEADER
# ====================================================================
def test_request_id_generated_and_returned():
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_custom_client_request_id_preserved():
    custom_id = "client-trace-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


# ====================================================================
# 3. STRUCTURED JSON LOGGING & SENSITIVE FIELD MASKING
# ====================================================================
def test_structured_json_logging_masks_sensitive_keys():
    formatter = StructuredJSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="User authenticated successfully",
        args=(),
        exc_info=None,
    )
    record.jwt_secret = "super_secret_jwt_token"
    record.password = "secret_password"
    record.user_id = "user123"

    formatted = formatter.format(record)
    log_dict = json.loads(formatted)

    assert log_dict["message"] == "User authenticated successfully"
    assert log_dict["user_id"] == "user123"
    assert "jwt_secret" not in log_dict
    assert "password" not in log_dict


# ====================================================================
# 4. REDIS RATE LIMITER BACKEND
# ====================================================================
class MockPipeline:
    def __init__(self, execute_result):
        self.execute_result = execute_result

    def incr(self, name, amount=1):
        pass

    def ttl(self, name):
        pass

    async def execute(self):
        return self.execute_result


@pytest.mark.anyio
async def test_redis_rate_limiter_backend_increment():
    mock_redis = MagicMock()
    mock_redis.expire = AsyncMock()
    mock_pipeline = MockPipeline(execute_result=[1, 60])
    mock_redis.pipeline.return_value = mock_pipeline

    backend = RedisRateLimiterBackend(redis_client=mock_redis)
    await backend.check("test_ip", max_requests=5, window_seconds=60, force=True)

    mock_redis.pipeline.assert_called_once()


@pytest.mark.anyio
async def test_redis_rate_limiter_backend_exceeded():
    mock_redis = MagicMock()
    mock_pipeline = MockPipeline(execute_result=[6, 45])
    mock_redis.pipeline.return_value = mock_pipeline

    backend = RedisRateLimiterBackend(redis_client=mock_redis)

    with pytest.raises(RateLimitExceeded) as exc_info:
        await backend.check("test_ip", max_requests=5, window_seconds=60, force=True)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "45"


# ====================================================================
# 5. CLAMAV MALWARE SCANNER BACKEND
# ====================================================================
@pytest.mark.anyio
async def test_clamav_malware_scanner_clean():
    mock_reader = AsyncMock()
    mock_reader.read.return_value = b"stream: OK\0"
    mock_writer = MagicMock()
    mock_writer.drain = AsyncMock()
    mock_writer.wait_closed = AsyncMock()

    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
        scanner = ClamAVMalwareScanner(host="localhost", port=3310)
        status_res = await scanner.scan_bytes(b"Clean file bytes", "clean.txt")
        assert status_res == ScanStatus.CLEAN


@pytest.mark.anyio
async def test_clamav_malware_scanner_infected():
    mock_reader = AsyncMock()
    mock_reader.read.return_value = b"stream: EICAR-Test-Signature FOUND\0"
    mock_writer = MagicMock()
    mock_writer.drain = AsyncMock()
    mock_writer.wait_closed = AsyncMock()

    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
        scanner = ClamAVMalwareScanner(host="localhost", port=3310)
        status_res = await scanner.scan_bytes(b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE", "virus.txt")
        assert status_res == ScanStatus.INFECTED


# ====================================================================
# 6. PRODUCTION VALIDATOR DEPLOYMENT CHECKS
# ====================================================================
def test_production_validator_redis_url_required():
    with pytest.raises(Exception, match="requires REDIS_URL"):
        Settings(
            environment="production",
            jwt_secret="a_very_long_valid_jwt_secret_string_32bytes_long",
            llm_api_key="valid-llm-key",
            cors_allowed_origins=["https://nyaya.ai"],
            allowed_hosts=["nyaya.ai"],
            rate_limit_backend="redis",
            redis_url=None,
        )


def test_production_validator_clamav_host_required():
    with pytest.raises(Exception, match="requires CLAMAV_HOST"):
        Settings(
            environment="production",
            jwt_secret="a_very_long_valid_jwt_secret_string_32bytes_long",
            llm_api_key="valid-llm-key",
            cors_allowed_origins=["https://nyaya.ai"],
            allowed_hosts=["nyaya.ai"],
            malware_scanner_type="clamav",
            clamav_host="",
        )
