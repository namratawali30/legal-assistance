# Demo 2 — Evidence-First Workflow & Consumer Rights Protection

**Target Duration**: 7 – 9 Minutes  
**Primary Domain**: `consumer_rights` (The Consumer Protection Act, 2019 / Defective Product & Deficiency in Service)  
**Key Features Highlighted**: Evidence Vault File Upload, SHA-256 Cryptographic Hashing, Multi-Document Text Extraction, Dual Citation Grounding (`[EVIDENCE_n]` + `[SOURCE_n]`), Evidence Gap Analysis, Action Planner, Complaint Finalization & Evidence Lock, and Lawyer Handoff Export.

---

## 🎯 Purpose & Scenario Overview

This demonstration showcases how Nyaya AI handles **user-supplied evidence documents**. The user uploads a purchase invoice and a customer support email transcript into the Evidence Vault. Nyaya AI validates file integrity using SHA-256 hashes, extracts text safely, integrates factual evidence with statutory law in chat, identifies missing evidence gaps, and exports a complete legal handoff pack.

---

## 📋 Synthetic Case Facts

- **Consumer**: Meera Kapoor (Fictional Consumer)
- **Seller / Manufacturer**: Apex Electronics Pvt. Ltd., Pune (Fictional Entity)
- **Product**: ApexBook Pro 14 Laptop (Price: INR 53,100, Invoice Date: 15-Jan-2026)
- **Grievance**: Hardware power failure 3 weeks post-purchase; authorized service center demanded INR 12,000 extra for repairs despite active 1-year warranty.
- **Evidence Files**:
  1. `docs/demos/assets/consumer_invoice.txt`
  2. `docs/demos/assets/consumer_support_exchange.txt`

---

## 🛠️ Pre-Demo Setup

1. Ensure local backend (`http://127.0.0.1:8000`) and frontend (`http://localhost:5173`) are running.
2. Ensure synthetic asset files exist in `docs/demos/assets/`.
3. Open browser at `http://localhost:5173`.
4. Register a fresh synthetic account:
   - **Email**: `meera.demo@example.test`
   - **Password**: `DemoPass123!`

---

## 🎬 Step-by-Step Demo Execution

### Step 1: Upload Documents to Evidence Vault
1. Navigate to **Evidence Vault** (`/evidence`).
2. Click **Upload Evidence**.
3. Select `docs/demos/assets/consumer_invoice.txt` and set document type to `Purchase Receipt / Invoice`.
   - **Result**: File uploads instantly. System computes SHA-256 fingerprint, performs security checks, extracts text, and sets status to `ready`.
4. Click **Upload Evidence** again.
5. Select `docs/demos/assets/consumer_support_exchange.txt` and set document type to `Correspondence / Email`.
   - **Result**: Second file processed successfully with status `ready`.

🗣️ **Presenter Talk Track**:
> *"Notice the Evidence Vault calculates a unique SHA-256 cryptographic hash for every file on upload. This ensures original evidence immutability and provenance tracking."*

---

### Step 2: Evidence-Aware Legal Chat
1. Navigate to **Legal Chat** (`/chat`).
2. Type the following prompt into the chat box:
   > *"I uploaded my purchase invoice and support emails for a laptop that broke under warranty. What are my legal remedies under the Consumer Protection Act 2019?"*
3. Click **Send**.

#### 🔍 Expected System Behavior
- **Dual Citation Grounding**: The assistant references factual invoice details using `[EVIDENCE_1]` and `[EVIDENCE_2]`, and statutory law using `[SOURCE_1]` (Consumer Protection Act, 2019).
- **Separation of Facts and Law**:
  - `[EVIDENCE_1]`: Laptop purchase date (15-Jan-2026) and price (INR 53,100).
  - `[EVIDENCE_2]`: Refusal of free warranty repair by Apex Customer Support.
  - `[SOURCE_1]`: Rights under Consumer Protection Act 2019 regarding defective goods and District Commission jurisdiction.

🗣️ **Presenter Talk Track**:
> *"Observe how Nyaya AI maintains a clear boundary between statutory law `[SOURCE_n]` and user evidence `[EVIDENCE_n]`. It cites exact evidence items alongside statutory sections."*

---

### Step 3: Case Readiness & Evidence Gap Analysis
1. Click **Case Readiness** in the header.
2. View the Readiness breakdown:
   - **Known Facts**: Purchase date, product model, warranty period, refusal of service.
   - **Attached Evidence**: 2 items verified (`consumer_invoice.txt`, `consumer_support_exchange.txt`).
   - **Evidence Gaps**: Missing formal written legal notice to seller, missing authorized service center job card.

🗣️ **Presenter Talk Track**:
> *"The Case Readiness assessment objectively flags missing evidence items that a lawyer or consumer commission will require before filing."*

---

### Step 4: Complaint Finalization & Evidence Lock
1. Navigate to **Complaints** (`/complaints`).
2. Click **Create New Complaint**.
3. Select domain `consumer_rights` and link both evidence items.
4. Click **Generate Complaint Draft**.
   - Review auto-populated complaint sections (Complainant details, Opposite Party details, Statement of Facts, Relief Sought).
5. Click **Finalize Complaint**.
   - **Security Lock Action**: Finalizing the complaint transitions its state to `finalized` and locks all linked evidence items, preventing accidental deletion or tampering.

---

### Step 5: Lawyer Handoff Pack Export
1. Click **Lawyer Handoff Pack** for the finalized complaint session.
2. Review the Handoff summary:
   - **Chronology**: Factual timeline derived from uploaded evidence.
   - **Evidence Index**: Complete table listing filenames, MIME types, and SHA-256 cryptographic hashes.
   - **Statutory References**: Relevant sections under Consumer Protection Act 2019.
3. Click **Export PDF** (or **Export DOCX**).
   - **Result**: Downloads a formatted document ready for presentation to legal counsel.

---

## 🛡️ Safety & Viva Evaluation Points

- **Cryptographic Provenance**: SHA-256 hashing guarantees evidence integrity.
- **Evidence Isolation**: Law and user evidence are never conflated in citations.
- **Finalization Locking**: Prevents deletion of evidence attached to finalized legal complaints.

---

## 🔄 Reset Instructions

1. Click **Sign Out**.
2. Register a new synthetic test account (e.g. `meera.demo2@example.test`).
