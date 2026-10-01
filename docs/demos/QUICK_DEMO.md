# Quick Demo Script — 3 to 4 Minute Viva Walkthrough

**Target Duration**: 3 – 4 Minutes  
**Purpose**: A fast-paced, high-impact demonstration designed for short academic viva evaluations, project reviews, or portfolio demos.

---

## ⏱️ Timeline & Step-by-Step Sequence

### 1. Project Introduction (0:00 – 0:30)
🗣️ **Presenter**:
> *"Nyaya AI is an AI-powered Indian legal assistance workspace. Unlike generic chatbots, it guides users through a safe, structured workflow: clarifying facts, retrieving verified legal statutes, organizing evidence, assessing case readiness, and generating lawyer-ready handoff packs."*

---

### 2. Follow-Up Clarification Engine (0:30 – 1:30)
1. Open **Legal Chat** (`/chat`).
2. Type prompt:
   > *"My senior keeps forcing me to do his work and threatens me when I refuse. What can I do?"*
3. Show system response: `ASK_FOLLOW_UP` question asking if "senior" is a student or corporate employee.
4. Reply:
   > *"He is a 4th-year student in my college."*

🗣️ **Presenter**:
> *"Notice that Nyaya AI does not guess the category. It asks a single targeted follow-up question, updates its structured context, and routes the query to `anti_ragging`."*

---

### 3. Grounded Legal RAG & Citation Inspection (1:30 – 2:30)
1. Show assistant response with `[SOURCE_1]` citation badge.
2. Click **`[SOURCE_1]`** to open `SourceDetailsModal` (showing UGC Anti-Ragging Regulations 2009).
3. Toggle top toolbar switch from **Simple** to **Detailed** mode to show expanded legal depth without changing citation sources.

🗣️ **Presenter**:
> *"Every legal assertion is strictly grounded in verified Indian statutes via local RAG retrieval. Clicking any citation opens the exact underlying legal provision."*

---

### 4. Case Readiness & Action Planner (2:30 – 3:30)
1. Click **Case Readiness** in header -> show factual completeness score, known facts, and missing evidence gaps.
   - *Presenter Note*: Explicitly state: *"This measures factual completeness, NOT probability of winning in court."*
2. Click **Legal Action Planner** -> show prioritized next steps (UGC helpline 1800-180-5522, Anti-Ragging Committee complaint).

---

### 5. Wrap-Up & Closing Statement (3:30 – 4:00)
🗣️ **Presenter**:
> *"In summary, Nyaya AI bridges the gap between raw legal grievances and structured legal action while maintaining strict fail-closed safety and citation grounding."*
