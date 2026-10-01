import logging
import json
import datetime
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

SENSITIVE_KEYS = {
    "jwt", "jwt_secret", "password", "token", "authorization", "secret",
    "access_key", "secret_key", "llm_api_key", "redis_url", "mongodb_url",
    "text", "content", "narrative", "extracted_text", "transcript", "evidence"
}


class StructuredJSONFormatter(logging.Formatter):
    """
    Formatter producing structured JSON log records with automatic masking of sensitive attributes.
    """

    def format(self, record: logging.LogRecord) -> str:
        from app.config import settings

        log_data = {
            "timestamp": datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": getattr(settings, "environment", "development"),
            "release_id": getattr(settings, "release_id", "dev-local"),
            "request_id": request_id_ctx.get(""),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Merge extra fields while filtering out sensitive keys
        if hasattr(record, "__dict__"):
            for key, val in record.__dict__.items():
                if key not in log_data and not key.startswith("_") and key.lower() not in SENSITIVE_KEYS:
                    if isinstance(val, (str, int, float, bool, list, dict)) or val is None:
                        log_data[key] = val

        return json.dumps(log_data)


def setup_production_logging():
    """Configures root logger with StructuredJSONFormatter."""
    from app.config import settings
    root_logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJSONFormatter())
    root_logger.handlers = [handler]
    log_level = logging.DEBUG if settings.environment == "development" else logging.INFO
    root_logger.setLevel(log_level)
