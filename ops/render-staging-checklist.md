# Nyaya AI Render Staging Deployment Operator Checklist

> [!IMPORTANT]
> This document outlines the exact manual sequence required to deploy the Nyaya AI staging environment to Render, MongoDB Atlas, and Cloudflare R2.
> Do not commit production or staging credentials to git.

---

## 1. Prerequisites & Account Setup

- [ ] **MongoDB Atlas**: Create a staging cluster database named `nyaya_ai_staging` and obtain standard connection string URI.
- [ ] **Cloudflare R2**: Create a private R2 bucket named `nyaya-private-evidence-staging` and generate an API Token with S3 Access Key ID & Secret Access Key. Set S3 Endpoint to `https://<account_id>.r2.cloudflarestorage.com`.
- [ ] **Render Account**: Connect GitHub repository `Nyaya-AI` to Render dashboard.

---

## 2. Render Blueprint Application

- [ ] Select **Blueprints** in Render Dashboard and click **New Blueprint Instance**.
- [ ] Choose repository `Nyaya-AI` and select region **Singapore**.
- [ ] Render will automatically discover `render.yaml` and plan 4 resources:
  1. `nyaya-ai-api-staging` (Web Service Docker)
  2. `nyaya-ai-staging` (Static Site React)
  3. `nyaya-ai-rate-limit-staging` (Key Value / Valkey)
  4. `nyaya-ai-clamav-staging` (Private Service ClamAV)

---

## 3. Environment Secret Configuration

In the Render Dashboard for `nyaya-ai-api-staging`, input the following **Manual Secrets**:

- [ ] `JWT_SECRET`: Random 32+ byte string (e.g. `generate_secure_random_hex_string_32bytes`)
- [ ] `MONGODB_URL`: MongoDB Atlas connection string (`mongodb+srv://...`)
- [ ] `OBJECT_STORAGE_BUCKET`: `nyaya-private-evidence-staging`
- [ ] `OBJECT_STORAGE_ENDPOINT`: `https://<account_id>.r2.cloudflarestorage.com`
- [ ] `OBJECT_STORAGE_ACCESS_KEY`: Cloudflare R2 Access Key ID
- [ ] `OBJECT_STORAGE_SECRET_KEY`: Cloudflare R2 Secret Access Key
- [ ] `LLM_API_KEY`: Staging Gemini/OpenAI API key

---

## 4. Post-First-Deploy URL Wiring

1. **Deploy Backend**: Click **Deploy** on `nyaya-ai-api-staging`. Once complete, copy the generated backend URL (e.g., `https://nyaya-ai-api-staging.onrender.com`).
2. **Update Backend CORS & Hosts**:
   - `CORS_ALLOWED_ORIGINS` = `https://nyaya-ai-staging.onrender.com`
   - `ALLOWED_HOSTS` = `nyaya-ai-api-staging.onrender.com`
3. **Update Frontend Environment**:
   - Set `VITE_API_BASE_URL` = `https://nyaya-ai-api-staging.onrender.com` in `nyaya-ai-staging` environment settings.
4. **Deploy Frontend**: Trigger deploy for `nyaya-ai-staging`.

---

## 5. Verification & Smoke Testing

- [ ] **Non-Destructive Smoke Test**:
  ```bash
  STAGING_BACKEND_URL=https://nyaya-ai-api-staging.onrender.com \
  STAGING_FRONTEND_URL=https://nyaya-ai-staging.onrender.com \
  python scripts/staging_smoke.py
  ```
- [ ] **EICAR Malware Scan Verification**: Upload EICAR test string TXT file to staging evidence vault and verify upload is blocked with HTTP 422 / malware detected error.
- [ ] **End-to-End Synthetic Flow**: Log in with synthetic staging account, send chat query, create complaint draft, upload clean TXT evidence, export PDF/DOCX, open Lawyer Handoff pack.

---

## 6. Rollback Sequence

If post-deploy verification fails:
1. In Render Dashboard, open `nyaya-ai-api-staging` -> **Deploys**.
2. Select the previous successful deployment revision (Git commit SHA).
3. Click **Rollback to this deploy**.
4. Repeat for `nyaya-ai-staging` static site.
