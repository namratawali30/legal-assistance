# Indian Legal Assistance & Documentation Platform

An AI-powered Indian legal assistance workspace designed to help citizens understand legal issues, organize evidence, explore practical next steps, prepare formal legal complaints, and generate lawyer-ready case handoff materials using citation-grounded Retrieval-Augmented Generation (RAG).

> [!IMPORTANT]
> **Legal Information Disclaimer**: This platform provides **legal information and organizational assistance**, NOT guaranteed professional legal advice, legal representation, or a replacement for a qualified advocate. For high-stakes legal matters, users should consult a licensed legal professional.

---

## 🎯 Platform Capabilities & Complete Product Workflow

Legal information in India is often complex, scattered across statutes, difficult to interpret for non-lawyers, and challenging to connect to specific facts. This platform bridges the gap between an initial problem description and actionable legal clarity:

1. **Guided Case Intake & Fact Structuring**: Collects complainant details, opposite party information, incident dates, locations, transaction amounts, and desired outcomes into a unified `Case/Matter` entity.
2. **Retrieves Grounded Law with Candidate Fusion**: Combines vector similarity (FAISS) with BM25 keyword matching via Reciprocal Rank Fusion (RRF) across verified Indian statutes.
3. **Deterministic Claim-Support Verification**: Verifies every generated material legal claim against exact supporting excerpts from authoritative legal sources before presenting answers.
4. **Organizes Case Evidence with OCR**: Provides an Evidence Vault supporting documents, images (with pytesseract OCR), scanned PDFs, audio, and video with SHA-256 integrity hashing and privacy protection.
5. **Assesses Case Readiness**: Computes objective factual completeness and evidence gap analysis to guide case preparation.
6. **Prepares Formal Complaints & Handoffs**: Automatically builds structured legal complaints and comprehensive Lawyer Handoff Packs exported to PDF and DOCX formats.
7. **Submission Tracking & Follow-up Reminders**: Allows users to record official submission acknowledgments (authority name, submission date, reference diary number) and set in-app follow-up reminders.

---

## 🔄 Core User Workflow

```mermaid
flowchart TD
    A[Guided Intake & Fact Structuring] --> B[Case / Matter Entity Created]
    B --> C[Candidate Fusion RAG Retrieval (FAISS + Keyword RRF)]
    C --> D[Deterministic Claim-Support Verification]
    D --> E[Citation-Grounded Response]
    E --> F[Evidence Upload & OCR Extraction]
    F --> G[Case Readiness & Gap Analysis]
    G --> H[Formal Complaint & Handoff Export (PDF/DOCX)]
    H --> I[User Submission Acknowledgment & Reminders]
```

---

## ✨ Key Upgrades & Architecture

### ⚖️ Grounded RAG & Retrieval Engine
- **Authenticated Legal Conversations**: User-owned chat sessions persisted securely in MongoDB.
- **Candidate Fusion Retrieval**: FAISS vector search combined with keyword BM25 scoring via Reciprocal Rank Fusion (RRF).
- **Deterministic Claim-Support Verification**: Rejects/abstains if generated material claims lack exact supporting excerpts in retrieved sources.
- **Answer Mode Toggle**: Switch between **Simple Mode** (concise practical summaries) and **Detailed Mode** (deep legal analysis).

### 📁 Evidence Vault & OCR Processing
- **Multi-Format Upload Support**: PDF (text & scanned), TXT, DOCX, JPG, PNG, WEBP, MP3, WAV, M4A, MP4, WebM.
- **Image & Scanned PDF OCR**: `pytesseract` and `pymupdf` image fallback for extracting text from scanned receipts, invoices, and screenshot evidence.
- **Cryptographic File Integrity**: SHA-256 fingerprinting calculated on upload to guarantee original evidence immutability.

### 📋 Cases & Matter Workspace
- **Structured Intake Facts**: Locations, incident dates, parties, transaction details, desired outcomes, and missing information.
- **Submission Recording**: Distinguishes "finalized in application" from "submitted to authority" via user-recorded filing acknowledgments.
- **In-App Follow-Up Reminders**: Track statutory response deadlines and hearing dates inside the workspace.

---

## 📚 Supported Legal Categories

1. `consumer_rights`: Defective goods, deficiency in service, unfair trade practices, Consumer Protection Act 2019.
2. `labour_rights`: Minimum wages, timely payment, wrongful termination, Code on Wages 2019.
3. `womens_safety`: Sexual harassment at workplace (POSH Act 2013), domestic violence (PWDVA 2005), emergency remedies.
4. `educational_rights`: Arbitrary fee hikes, admission disputes, 25% EWS quota, Right to Education Act 2009.
5. `anti_ragging`: Campus ragging, harassment, institutional non-compliance, UGC Anti-Ragging Regulations.

---

## 🚀 Setup & Execution Guide

### Prerequisites
- **Python**: 3.12 (pin documented in `.python-version`)
- **Node.js**: v20 or higher
- **MongoDB**: Local MongoDB instance running on port 27017 or Docker service.
- **Tesseract OCR & Poppler**: Installed on host system for OCR and PDF image rendering.

### Local Development Setup

1. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   cp backend/.env.example backend/.env
   ```

2. **Start Backend Service**:
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. **Start Frontend Workspace** (in a new terminal):
   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```
   Open browser at `http://localhost:5173`.

4. **Run Docker Compose** (Full Local Environment):
   ```bash
   docker-compose up --build
   ```

---

## 🧪 Verification & Test Baselines

All test suites and build checks execute deterministically without requiring paid external API credentials:

| Suite | Scope | Baseline Status |
| :--- | :--- | :---: |
| **Backend Pytest** | Unit, integration, case workflow, claim verification, readiness & security tests | **467 / 467 passed** (0 regressions) |
| **Frontend Production Build** | Vite client production bundle (`npm run build`) | **PASS** (115 modules transformed) |
| **GitHub Actions CI** | Automated workflow for backend tests & frontend checks | **Configured (`.github/workflows/ci.yml`)** |
| **System Health Probes** | `/health/liveness` & `/health/readiness` database, vector index, and storage checks | **PASS** |

---

## 🔒 Security, Privacy & Operational Controls

- **Authentication & Authorization**: Password hashing via bcrypt, HS256 JWT tokens, and strict server-side ownership checks (`user_id == current_user["_id"]`) on all case, evidence, complaint, and reviewer endpoints.
- **Redacted Logging & Request Correlation**: `X-Request-ID` middleware with context tracking; tokens, passwords, and sensitive evidence text are excluded from logs.
- **Storage Abstraction**: Modular storage provider (`local` for development, `s3` for cloud storage).
- **Health Probes**: Liveness (`/health/liveness`) and readiness (`/health/readiness`) endpoints checking Mongo connectivity, vector index existence, and storage readiness.

---

## ⚠️ Known Limitations & Deployment Notes

1. **Qualified Legal Review**: Generated complaint drafts and action plans are for organizational assistance and general awareness. They do not constitute filing-ready legal representations without advocate review.
2. **Category Scope**: Grounded RAG is scoped strictly to the 5 supported domains. Out-of-scope legal queries (e.g. income tax disputes, criminal proceedings, real estate title disputes) are safely refused.
