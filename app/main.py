from contextlib import asynccontextmanager

import logging

logger = logging.getLogger(__name__)

from app.db.indexes import create_indexes
from fastapi.responses import JSONResponse
from app.database import database
from fastapi import (
    FastAPI,
    Request,
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
        # Never expose unexpected database,
        # filesystem, library, path, or provider
        # exception details to API clients.
        #
        # Detailed diagnostics will be handled
        # by internal logging in 09.14.
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


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(complaint_router)
app.include_router(complaint_export_router)
app.include_router(evidence_router)


@app.get(
    "/health",
    tags=["Health"],
)
async def health_check():
    return {
        "status": "ok",
    }
