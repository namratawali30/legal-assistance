# Nyaya AI — Usability Testing Protocol

This document outlines the student-project usability testing protocol, tester profiles, task catalog, evaluation criteria, and severity classification rules for **Nyaya AI**.

> [!NOTE]
> **Methodology Note**: As a local student project, testing was conducted through structured internal developer/evaluator walkthroughs and supervised synthetic rehearsal sessions. No sensitive real-world legal data or real-user legal disputes were collected.

---

## 1. Usability Tester Profiles

To evaluate Nyaya AI across different user personas and device modalities, five generic tester profiles were established:

1. **Profile A: First-Time Non-Technical Citizen**  
   *Goal*: Describe an unfamiliar legal grievance in plain language and discover practical next steps without getting overwhelmed by legal jargon.
2. **Profile B: Student Project Presenter / Evaluator**  
   *Goal*: Complete an end-to-end demonstration smoothly during a live viva presentation without encountering unexpected UI dead-ends.
3. **Profile C: Evidence-Heavy User**  
   *Goal*: Upload multiple evidence files (invoices, emails, notes), verify cryptographic status, understand missing evidence gaps, and export a complaint pack.
4. **Profile D: Mobile Viewport User**  
   *Goal*: Navigate legal chat, inspect source details, and manage evidence on a narrow mobile screen (375px – 430px).
5. **Profile E: Keyboard & Assistive Technology User**  
   *Goal*: Navigate primary application views using `Tab`, `Enter`, `Space`, and `Escape` with visible focus indicators and modal focus trapping.

---

## 2. Core Usability Task Catalog (20 Tasks)

| Task ID | Task Description | Target View | Success Criteria |
| :--- | :--- | :--- | :--- |
| **UT-01** | Account Registration & Login | `/register`, `/login` | Successful token issue & redirect to Dashboard |
| **UT-02** | Initial Dashboard Orientation | `/` | Obvious primary call-to-action ("Start Legal Chat") |
| **UT-03** | Starting New Legal Chat | `/chat` | Clean session initialized with active input composer |
| **UT-04** | Ambiguous Query Handling | `/chat` | Receives targeted single follow-up question |
| **UT-05** | Responding to Follow-Up | `/chat` | Resolves category & stores structured case context |
| **UT-06** | Identifying Legal Disclaimer | All pages | Visible legal information disclaimer in header/footer |
| **UT-07** | Inspecting Interactive Citations | `/chat` | Clicking `[SOURCE_n]` opens `SourceDetailsModal` |
| **UT-08** | Toggling Simple / Detailed Mode | `/chat` | Switches answer depth without altering legal sources |
| **UT-09** | Opening Case Readiness View | Header modal | Displays completeness score & missing evidence gaps |
| **UT-10** | Viewing Legal Action Planner | Header modal | Shows ordered next steps & primary action callout |
| **UT-11** | Uploading Document Evidence | `/evidence` | File uploads, computes SHA-256, reaches `ready` state |
| **UT-12** | Uploading Audio/Video Evidence | `/evidence` | Audio extracts transcript; video explains transcript scope |
| **UT-13** | Understanding Image / Non-Text Status | `/evidence` | Shows clear "Requires OCR" badge without crashing |
| **UT-14** | Creating Complaint Draft | `/complaints` | Draft complaint populated from chat/evidence facts |
| **UT-15** | Editing & Finalizing Complaint | `/complaints` | Edits saved; finalization locks linked evidence |
| **UT-16** | Exporting Lawyer Handoff Pack | Modal / `/complaints` | Generates formatted PDF / DOCX summary files |
| **UT-17** | Session Expiry & Unauthorized Handling | Protected routes | Invalid token clears session & redirects to `/login` |
| **UT-18** | Mobile Viewport Navigation | Mobile drawer | All primary navigation & modals accessible on 375px |
| **UT-19** | Keyboard Modal Trap & Dismissal | Modals | Focus trapped inside modal; `Escape` closes modal |
| **UT-20** | User Sign Out | Header menu | Clears token from `sessionStorage` & returns to login |

---

## 3. Severity Classification Framework

Observed usability issues are classified into four severity tiers:

- **P0 — Blocker**: Core workflow impossible, security/privacy violation, data loss, or misleading legal claim. (*Must be 0 open*).
- **P1 — High**: User cannot complete an important task without assistance or significant effort. (*Must be 0 open*).
- **P2 — Medium**: Minor confusion or sub-optimal UX, but task remains completable. (*Documented & resolved where high-value*).
- **P3 — Low**: Minor cosmetic or visual polish item. (*Permitted if non-disruptive*).

---

## 4. Evaluation Execution & Acceptance Target

- **P0 Open**: 0
- **P1 Open**: 0
- **Automated Regression**: 424 backend tests green, 112 frontend modules built, 12 Playwright E2E smoke tests green, 60 RAG eval scenarios green (0 critical safety failures).
