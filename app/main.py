from fastapi import FastAPI

from app.config import settings


app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend API for an AI-powered legal assistance "
        "application using Retrieval-Augmented Generation."
    ),
    version=settings.app_version,
)


@app.get("/")
async def root():
    return {
        "message": "AI Legal Assistance API is running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.environment,
    }