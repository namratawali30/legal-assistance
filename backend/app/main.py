from contextlib import asynccontextmanager

import logging

logger = logging.getLogger(__name__)

from app.db.indexes import create_indexes
from fastapi.responses import JSONResponse
from app.database import database
from fastapi import (
    FastAPI,
    Request,
    status,
)
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router

from app.config import settings
from app.database import (
    check_database_connection,
    close_database_connection,
)
from app.api.complaint import (
    router as complaint_router,
)
from app.api.complaint_export import (
    router as complaint_export_router,
)
from app.api.evidence import (
    router as evidence_router,
)
from app.repositories.evidence_repository import (
    ensure_evidence_indexes,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting.")

    try:
        database_available = await check_database_connection()

        if not database_available:
            raise RuntimeError(
                "Database connection unavailable " "during application startup."
            )

        logger.info("Database connection established.")

        # Core indexes and integrity-critical evidence
        # indexes must both exist before requests are
        # accepted.
        await create_indexes()

        await ensure_evidence_indexes()

        logger.info("Database indexes initialized.")

        yield

    finally:
        logger.info("Application shutting down.")

        await close_database_connection()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend API for an AI-powered legal assistance "
        "application using Retrieval-Augmented Generation."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

# -------------------------------------------------
# CORS & TRUSTED HOST MIDDLEWARE
# -------------------------------------------------
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

allowed_origins = settings.cors_allowed_origins
if isinstance(allowed_origins, str):
    allowed_origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

allowed_hosts = settings.allowed_hosts
if isinstance(allowed_hosts, str):
    allowed_hosts = [h.strip() for h in allowed_hosts.split(",") if h.strip()]
if settings.environment != "production":
    if "*" not in allowed_hosts:
        allowed_hosts = list(set(allowed_hosts + ["localhost", "127.0.0.1", "testserver", "*"]))

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts,
)


@app.middleware("http")
async def add_response_security_headers(
    request: Request,
    call_next,
):
    try:
        response = await call_next(
            request
        )

    except Exception:
        logger.exception(
            "Unhandled API request failure."
        )
        response = JSONResponse(
            status_code=500,
            content={
                "detail":
                    "Internal server error."
            },
        )

    # -------------------------------------------------
    # BASELINE SECURITY HEADERS
    # -------------------------------------------------

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

    # -------------------------------------------------
    # PRIVATE API RESPONSES
    # -------------------------------------------------
    #
    # Authentication, chats, complaints, evidence
    # metadata and API errors may contain user-specific
    # or otherwise sensitive information.
    #
    # Existing download endpoints already provide their
    # own stronger cache headers. Do not overwrite them.
    # -------------------------------------------------

    if request.url.path.startswith("/api/v1/"):
        if not response.headers.get("Cache-Control"):
            response.headers["Cache-Control"] = "no-store, private"

        if not response.headers.get("Pragma"):
            response.headers["Pragma"] = "no-cache"

        existing_vary = response.headers.get(
            "Vary",
            "",
        )

        vary_values = {
            item.strip() for item in (existing_vary.split(",")) if item.strip()
        }

        vary_values.add("Authorization")

        response.headers["Vary"] = ", ".join(sorted(vary_values))

    return response


from app.api.readiness import router as readiness_router
from app.api.action_plan import router as action_plan_router
from app.api.lawyer_handoff import router as lawyer_handoff_router
from app.api.case import router as case_router

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(complaint_router)
app.include_router(complaint_export_router)
app.include_router(evidence_router)
app.include_router(readiness_router)
app.include_router(action_plan_router)
app.include_router(lawyer_handoff_router)
app.include_router(case_router)





import uuid
from app.core.logging_config import request_id_ctx, setup_production_logging

setup_production_logging()


@app.middleware("http")
async def add_request_correlation_id(request: Request, call_next):
    client_request_id = request.headers.get("X-Request-ID")
    if client_request_id and len(client_request_id) <= 64:
        req_id = client_request_id.strip()
    else:
        req_id = str(uuid.uuid4())

    token = request_id_ctx.set(req_id)
    request.state.request_id = req_id

    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
    finally:
        request_id_ctx.reset(token)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


@app.get("/health/liveness", tags=["Health"])
async def liveness_probe():
    return {"status": "ok", "liveness": "alive"}


@app.get("/version", tags=["Health"])
async def version_check():
    return {
        "version": settings.app_version,
        "release_id": getattr(settings, "release_id", "1.0.0"),
        "environment": settings.environment,
    }


@app.get("/readiness", tags=["Health"])
@app.get("/health/readiness", tags=["Health"])
async def system_readiness_probe():
    checks = {}
    is_ready = True

    # 1. Mongo check
    try:
        db_ok = await check_database_connection()
        checks["database"] = "ok" if db_ok else "unavailable"
        if not db_ok:
            is_ready = False
    except Exception:
        checks["database"] = "error"
        is_ready = False

    # 2. Vector index check
    try:
        from app.rag.retriever import INDEX_PATH, METADATA_PATH
        if INDEX_PATH.exists() and METADATA_PATH.exists():
            checks["retrieval_index"] = "ok"
        else:
            checks["retrieval_index"] = "missing_index_files"
            is_ready = False
    except Exception:
        checks["retrieval_index"] = "error"
        is_ready = False

    # 3. Storage backend check
    try:
        from app.storage import get_storage_backend
        backend = get_storage_backend()
        checks["storage"] = "ok"
    except Exception:
        checks["storage"] = "error"
        is_ready = False

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "checks": checks,
        },
    )
