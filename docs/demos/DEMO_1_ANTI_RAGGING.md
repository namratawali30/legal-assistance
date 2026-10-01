# Demo 1 — Conversation-First Legal Guidance & Anti-Ragging Workflow

**Target Duration**: 5 – 7 Minutes  
**Primary Domain**: `anti_ragging` (UGC Anti-Ragging Regulations 2009 / IPC & BNS Harassment Provisions)  
**Key Features Highlighted**: Follow-Up Clarification Engine, Case Context Persistence, Grounded Legal RAG, Interactive Citations, Simple/Detailed Mode Toggle, Case Readiness Assessment, Legal Action Planner, Complaint Generation, and Lawyer Handoff Pack.

---

## 🎯 Purpose & Scenario Overview

This demonstration showcases Nyaya AI's ability to handle **ambiguous initial user prompts** safely. Rather than guessing whether a "senior" is a corporate manager or a college student, the system asks a single targeted follow-up question. Once clarified, it retrieves authoritative anti-ragging statutes, assesses factual completeness, generates actionable steps, and prepares a formal complaint.

---

## 📋 Synthetic Case Facts

- **Victim**: Aarav Sharma (Fictional 1st Year Student)
- **Institution**: Example National College of Technology, Pune
- **Perpetrator**: Vikram Singh (Fictional 4th Year Senior Student)
- **Grievance**: Forced lab assignment work, late-night hostel standing harassment, verbal threats of academic sabotage.

---

## 🛠️ Pre-Demo Setup

1. Ensure local backend (`http://127.0.0.1:8000`) and frontend (`http://localhost:5173`) are running.
2. Open browser at `http://localhost:5173`.
3. Register a fresh synthetic account:
   - **Email**: `aarav.demo@example.test`
   - **Password**: `DemoPass123!`

---

## 🎬 Step-by-Step Demo Execution

### Step 1: Initial Ambiguous Prompt
1. Navigate to **Legal Chat** (`/chat`).
2. Type the following ambiguous query into the prompt input:
   > *"My senior keeps forcing me to do his work and threatens me when I refuse. What can I do?"*
3. Click **Send**.

#### 🔍 Expected System Behavior
- **Decision Engine Output**: `ASK_FOLLOW_UP`
- **Assistant Response**:
  > *"To provide accurate legal guidance, could you clarify whether this senior is a fellow student at your college/university, or a senior employee/manager at your workplace?"*

🗣️ **Presenter Talk Track**:
> *"Notice that Nyaya AI does not jump to conclusions or invent a legal category. Because 'senior' can refer to workplace harassment or campus ragging, it asks one precise clarifying question."*

---

### Step 2: Context Clarification & Category Resolution
1. Type the clarification response:
   > *"He is a 4th-year student in my college."*
2. Click **Send**.

#### 🔍 Expected System Behavior
- **Category Resolution**: `anti_ragging`
- **Assistant Response**: Returns a citation-grounded explanation citing the **UGC Regulations on Curbing the Menace of Ragging in Higher Educational Institutions, 2009** and relevant penal provisions.
- **Sources Rendered**: `[SOURCE_1]`, `[SOURCE_2]` badges attached to statutory claims.

🗣️ **Presenter Talk Track**:
> *"Once clarified, the system updates its structured case context, routes the query to the `anti_ragging` domain, and retrieves authoritative legal provisions instead of hallucinating advice."*

---

### Step 3: Interactive Citation & Answer Mode Toggle
1. Click on the **`[SOURCE_1]`** citation badge inside the chat message.
   - **Modal Opens**: `SourceDetailsModal` showing Act Title (*UGC Anti-Ragging Regulations 2009*), provision summary, and official reference.
   - Press **Escape** or click **Close** to dismiss.
2. Toggle the **Answer Mode** switch in the top toolbar from **Simple** to **Detailed**.
   - **Result**: The response expands into deeper statutory analysis while preserving the exact same legal sources and citation grounding.

---

### Step 4: Case Readiness & Legal Action Planner
1. Click the **Case Readiness** button in the header toolbar.
   - **Visual Readiness View**: Shows factual completeness score (~65%), known facts (student identity, campus setting), and missing evidence (written complaint to Anti-Ragging Committee, incident dates).
   - *Presenter Callout*: Highlight that this score measures **completeness**, not probability of winning in court.
2. Click **Legal Action Planner**.
   - **Ordered Steps**:
     1. File an urgent complaint with the College Anti-Ragging Committee / Helpline (`1800-180-5522`).
     2. Submit a formal written grievance to the Head of Institution.
     3. Lodge an FIR under IPC/BNS if physical threats persist.

---

### Step 5: Complaint Generation & Lawyer Handoff
1. Click **Generate Complaint**.
   - Select category `anti_ragging` and click **Create Draft**.
   - Review auto-populated complaint sections (Complainant, Respondent, Factual Narrative, Legal Grounds).
   - Click **Finalize Complaint** to lock state.
2. Click **Lawyer Handoff Pack**.
   - View structured summary pack (Chronology, Legal Sources, Evidence Index, Action Plan).
   - Click **Export PDF** or **Export DOCX** to download client-ready files.

---

## 🛡️ Safety & Viva Evaluation Points

- **No Category Forcing**: The system cleanly separated workplace harassment from campus ragging.
- **Fail-Closed Retrieval**: Every legal assertion is linked to verified UGC/statutory sources.
- **Readiness Metric Safety**: Clearly framed as factual completeness, avoiding misleading win-rate claims.

---

## 🔄 Reset Instructions

To reset before another presentation run:
1. Click **Sign Out** in the top navigation.
2. Register another synthetic test account (e.g. `aarav.demo2@example.test`).
