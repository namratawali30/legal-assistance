import os
import sys

os.environ["ENVIRONMENT"] = "test"
os.environ["MONGODB_DATABASE"] = "ai_legal_assistance_e2e_db"
os.environ["LLM_API_KEY"] = "mock"
if "MONGODB_URL" not in os.environ:
    os.environ["MONGODB_URL"] = "mongodb://localhost:27017"
if "JWT_SECRET" not in os.environ:
    os.environ["JWT_SECRET"] = "e2e_test_jwt_secret_key_32_characters_minimum_length_required"

if __name__ == "__main__":
    from app.main import app
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


