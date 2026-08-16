from contextlib import asynccontextmanager
from app.db.indexes import create_indexes
from app.database import database
from fastapi import FastAPI
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router

from app.config import settings
from app.database import (
    check_database_connection,
    close_database_connection,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting application...")

    database_available = await check_database_connection()

    if database_available:
        print("MongoDB connection Successful.")
        await create_indexes()
        print("Database indexes created.")
    else:
        print("WARNING: MongoDB connection failed.")

    yield

    print("Shutting down application...")
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
app.include_router(auth_router)
app.include_router(chat_router)


# @app.get("/")
# async def root():
#     return {
#         "message": "AI Legal Assistance API is running"
#     }

@app.on_event("startup")
async def startup_event():
    await create_indexes()

@app.get("/health")
async def health_check():
    database_available = await check_database_connection()

    return {
        "status": "healthy" if database_available else "unhealthy",
        "environment": settings.environment,
        "database": "connected" if database_available else "disconnected",
    }

