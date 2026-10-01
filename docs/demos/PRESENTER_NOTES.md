# Nyaya AI — Presenter Notes & Viva Defense Guide

This guide provides presenter talk tracks, architectural explanations, safety points, and answers to expected evaluator questions for academic vivas, portfolio walkthroughs, and project demonstrations.

---

## 🎙️ Project Pitch (~30 Seconds)

> *"Nyaya AI is an AI-powered Indian legal assistance workspace designed to help citizens understand legal issues, organize evidence, assess case readiness, prepare formal complaints, and generate lawyer-ready handoff packs using citation-grounded Retrieval-Augmented Generation (RAG). Instead of simply generating unverified text, it enforces strict fail-closed safety and citation grounding across five core Indian legal domains."*

---

## 💡 What Makes Nyaya AI Different From ChatGPT?

| Dimension | Generic LLM (e.g. ChatGPT) | Nyaya AI |
| :--- | :--- | :--- |
| **Legal Grounding** | Unconstrained generation; prone to statute hallucination | Strict RAG retrieval over verified Indian statutory corpus |
| **Clarification** | Often guesses user context or gives generic lists | Targeted single follow-up questions to complete facts |
| **Evidence Handling** | Unstructured text input only | SHA-256 evidence vault with metadata extraction & locking |
| **Citation System** | Generic text references (often unverified) | Dual isolation: `[SOURCE_n]` for law vs `[EVIDENCE_n]` for user facts |
| **Case Readiness** | None | Objective factual completeness and gap analysis |
| **Legal Artifacts** | Raw unstructured prose | Structured Complaints & Lawyer Handoff Packs (PDF/DOCX) |

---

## ❓ Common Viva Questions & Model Answers

### Q1: "How do you prevent the AI from hallucinating laws or sections?"
**Answer**:
> *"We implement a dual-layer safety model: First, a local vector database (FAISS) indexes verified Indian statutes. The LLM is restricted to generating legal claims only when backed by retrieved context. Second, our RAG evaluation suite continuously tests against forbidden claims and fake statutes. If retrieval confidence falls below threshold, the system fails closed rather than fabricating law."*

### Q2: "Where does the legal statutory knowledge come from?"
**Answer**:
> *"Our statutory knowledge base contains curated official Indian acts (such as Consumer Protection Act 2019, UGC Anti-Ragging Regulations 2009, POSH Act 2013, Factories Act, and RTE Act). We also integrate with India Code's digital repository for live statutory verification."*

### Q3: "Does Nyaya AI replace a human lawyer?"
**Answer**:
> *"No. Nyaya AI provides legal information and organizational assistance, not licensed legal advice or representation. Its primary goal is to prepare citizens with organized facts, evidence, and clear legal summaries so they can interact effectively with advocates or legal aid authorities."*

### Q4: "How is user evidence protected and secured?"
**Answer**:
> *"User uploaded evidence is stored with cryptographic SHA-256 hashing to guarantee original file immutability. All API endpoints enforce strict server-side ownership checks (`user_id == current_user["_id"]`), ensuring extracted text and files are private to the authenticated owner. In production architecture, evidence is stored in private S3/R2 buckets accessible only via short-lived signed URLs."*

### Q5: "Can the Case Readiness score predict if a user will win in court?"
**Answer**:
> *"No. We intentionally design Case Readiness as a factual and evidence completeness metric (e.g., whether dates, receipts, witness names, and statutory notices exist), NOT a legal prediction of court outcomes. Predicting court decisions with AI is unsafe and legally ungrounded."*

### Q6: "How do you test the quality and safety of legal responses?"
**Answer**:
> *"We maintain a 60-scenario RAG evaluation benchmark (`tests/test_rag_evaluation.py`) covering 54 supported legal scenarios and 6 out-of-scope refusal scenarios. The benchmark validates domain routing, citation accuracy, statute hallucination detection, prompt injection resistance, and law vs. evidence separation."*

### Q7: "Why does Nyaya AI support only five legal categories?"
**Answer**:
> *"To guarantee high precision and zero critical safety failures, we focused on five well-defined domains of Indian law: Consumer Rights, Labour Rights, Women's Safety, Educational Rights, and Anti-Ragging. Queries outside these domains trigger a safe refusal response instead of ungrounded answers."*

### Q8: "Why is the project finalized as a local/demo application rather than deployed live?"
**Answer**:
> *"Nyaya AI was developed as a demo-ready student project baseline. While all production artifacts—including Dockerfiles, Docker Compose topologies, Cloudflare R2 S3 storage drivers, Valkey rate limiters, ClamAV scanner interfaces, and Render Blueprint specs (`render.yaml`)—were fully implemented and verified green, live cloud deployment was intentionally skipped to keep local evaluation simple and zero-cost."*

### Q9: "What would be required to deploy Nyaya AI to live cloud infrastructure?"
**Answer**:
> *"Deploying live requires applying the repository's `render.yaml` Blueprint on Render, provisioning a MongoDB Atlas database, creating a Cloudflare R2 bucket, setting production environment secrets (`JWT_SECRET`, `MONGODB_URL`, `LLM_API_KEY`), and updating CORS allowed origins."*
