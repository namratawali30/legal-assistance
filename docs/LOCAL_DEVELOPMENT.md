# Nyaya AI — Local Development Guide

This guide provides step-by-step instructions to set up, configure, run, and debug **Nyaya AI** locally on a development machine.

---

## 1. Prerequisites

Before starting, ensure you have the following installed:

- **Python**: Version `3.12` or higher (`python --version`)
- **Node.js**: Version `20.x` or higher (`node --version`)
- **Git**: (`git --version`)
- **MongoDB**: Either a local MongoDB instance running on `mongodb://localhost:27017` OR a free MongoDB Atlas connection string.
- **ffmpeg** (Optional): Required if you plan to test local audio/video evidence transcription.

---

## 2. Backend Setup & Local Startup

Commands are written for **Windows PowerShell** (repository-relative paths):

1. Navigate to the backend directory:
   ```powershell
   cd backend
   ```

2. Create a virtual environment:
   ```powershell
   python -m venv venv
   ```

3. Activate the virtual environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

4. Install backend dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Configure local environment variables:
   Create a file named `.env` in the `backend/` root directory:
   ```env
   APP_NAME=AI Legal Assistance API
   APP_VERSION=0.1.0
   ENVIRONMENT=development

   MONGODB_URL=mongodb://localhost:27017
   MONGODB_DATABASE=nyaya_dev

   JWT_SECRET=development_jwt_secret_must_be_at_least_32_bytes_long
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30

   LLM_API_KEY=your_gemini_or_llm_api_key_here

   STORAGE_BACKEND=local
   RATE_LIMIT_BACKEND=memory
   MALWARE_SCANNER_TYPE=mock
   ```

6. Start the FastAPI development server:
   ```powershell
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   The backend API will be available at `http://127.0.0.1:8000`.
   Interactive OpenAPI documentation is accessible at `http://127.0.0.1:8000/docs`.

---

## 3. Frontend Setup & Local Startup

1. Open a new terminal window and navigate to the `frontend/` directory:
   ```powershell
   cd frontend
   ```

2. Install Node dependencies:
   ```powershell
   npm ci
   ```

3. Start the Vite development server:
   ```powershell
   npm run dev
   ```
   The frontend will be accessible in your browser at `http://localhost:5173`.

---

## 4. How Frontend Connects to Backend

In local development, the React frontend connects to the FastAPI backend using Vite's built-in development proxy (`frontend/vite.config.js`):

```js
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
```

This configuration routes all frontend requests matching `/api/*` to `http://127.0.0.1:8000/api/*`. This avoids CORS preflight issues during local development and allows the client to send relative requests (e.g. `axios.get('/api/v1/auth/me')`).

---

## 5. Environment Variables Reference (`backend/app/config.py`)

| Setting Name | Environment Default | Description |
| :--- | :--- | :--- |
| `environment` | `development` | Environment mode (`development`, `test`, `staging`, `production`) |
| `mongodb_url` | `mongodb://localhost:27017` | MongoDB connection URI |
| `mongodb_database` | `legal_assistance` | Target MongoDB database name |
| `jwt_secret` | *(Required in prod)* | Signing key for JWT auth tokens (min 32 bytes) |
| `llm_api_key` | *(Optional in dev)* | API key for Gemini / LLM legal response generation |
| `storage_backend` | `local` | Evidence storage driver (`local` or `s3`) |
| `rate_limit_backend` | `memory` | Rate limiter driver (`memory` or `redis`) |
| `malware_scanner_type` | `mock` | Scanner driver (`mock`, `clamav`, or `disabled`) |
| `cors_allowed_origins` | `["http://localhost:5173"]` | Allowed HTTP origins for CORS policy |
| `allowed_hosts` | `["*"]` in dev | Allowed HTTP host headers (`TrustedHostMiddleware`) |

---

## 6. Optional Audio / Video Transcription

For local processing of MP3, WAV, M4A audio files or MP4, WebM video files:

1. Download `ffmpeg` binaries for Windows from [ffmpeg.org](https://ffmpeg.org/download.html).
2. Extract and add the `bin/` folder (containing `ffmpeg.exe`) to your system `PATH`.
3. Verify installation:
   ```powershell
   ffmpeg -version
   ```

---

## 7. Troubleshooting Common Local Errors

### `Database connection unavailable during application startup`
- **Cause**: Backend cannot reach MongoDB.
- **Fix**: Ensure your local MongoDB service is running (`net start MongoDB` or `mongod`), or check that `MONGODB_URL` in `backend/.env` is correct.

### `401 Unauthorized` on API calls
- **Cause**: JWT token missing or expired in browser session.
- **Fix**: Log out and log back in, or clear `sessionStorage` in DevTools.

### `503 Service Unavailable` on Live LLM Answers
- **Cause**: `LLM_API_KEY` is missing or invalid in `backend/.env`.
- **Fix**: Set a valid LLM API key in `backend/.env` and restart uvicorn. Note that automated unit and RAG evaluation tests run using deterministic mocks without requiring a live LLM key.
