# Nyaya AI — End-to-End Demonstration Suite

This directory contains polished, repeatable demonstration scripts and synthetic test assets designed for academic project presentations, vivas, portfolio walkthroughs, and evaluator reviews.

---

## 📂 Demo Index & Materials

| Document | Focus Area | Domain | Target Duration |
| :--- | :--- | :--- | :---: |
| [**Demo 1: Conversation-First Guidance**](DEMO_1_ANTI_RAGGING.md) | Clarification Engine, Follow-Up, Grounded RAG, Citations, Action Plan | `anti_ragging` | **5 – 7 Min** |
| [**Demo 2: Evidence-First Workflow**](DEMO_2_CONSUMER_EVIDENCE.md) | Evidence Vault Upload, SHA-256 Hashing, Dual Citations, Complaint Lock | `consumer_rights` | **7 – 9 Min** |
| [**Quick Demo: Viva Elevator Pitch**](QUICK_DEMO.md) | High-impact condensed walkthrough for short evaluations | Multi-domain | **3 – 4 Min** |
| [**Presenter Notes & Viva Defense**](PRESENTER_NOTES.md) | Talk tracks, differentiator pitch, and answers to 9 common viva questions | N/A | Reference |

---

## 📁 Synthetic Demo Assets (`docs/demos/assets/`)

- `consumer_invoice.txt`: Synthetic purchase receipt for ApexBook Pro 14 laptop (INR 53,100).
- `consumer_support_exchange.txt`: Synthetic customer support email correspondence refusing warranty repair.
- `anti_ragging_notes.txt`: Synthetic incident statement describing hostel harassment.

> [!NOTE]
> All names, dates, companies, receipts, and incident details in demo assets are **100% synthetic and fictional**. No real personal data or commercial receipts are used.

---

## ⚡ Quick Start for Demonstrators

1. **Start Services**: Ensure local backend (`http://127.0.0.1:8000`) and frontend (`http://localhost:5173`) are running.
2. **Open Application**: Navigate to `http://localhost:5173`.
3. **Select Script**: Open [DEMO_1_ANTI_RAGGING.md](DEMO_1_ANTI_RAGGING.md) for conversation-first demo or [DEMO_2_CONSUMER_EVIDENCE.md](DEMO_2_CONSUMER_EVIDENCE.md) for evidence-first demo.
4. **Follow Prompts**: Use exact inputs and presenter talk tracks specified in the scripts.
