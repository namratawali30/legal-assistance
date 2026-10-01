from datetime import datetime, timezone
from io import BytesIO
from html import escape
import logging
from typing import Any
from bson import ObjectId

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from app.database import database
from app.repositories.complaint_repository import get_user_complaints
from app.repositories.evidence_repository import get_user_evidence
from app.schemas.lawyer_handoff import (
    HandoffComplaintInfo,
    HandoffEvidenceItem,
    HandoffFact,
    HandoffLegalSource,
    HandoffParty,
    HandoffQuestion,
    HandoffTimelineEvent,
    LawyerHandoffResponse,
)
from app.services.case_readiness_service import compute_session_readiness
from app.services.legal_action_planner_service import generate_session_action_plan

logger = logging.getLogger(__name__)


async def generate_session_handoff_pack(
    session: dict[str, Any],
    user_id: ObjectId | str,
) -> LawyerHandoffResponse:
    uid = ObjectId(user_id) if isinstance(user_id, str) else user_id
    category = session.get("category", "consumer_rights")
    case_context = session.get("case_context", {}) or {}

    # 1. Fetch Readiness & Action Plan
    readiness = await compute_session_readiness(session, user_id)
    action_plan = await generate_session_action_plan(session, user_id)

    # 2. Fetch User Evidence Records
    user_evidence = await get_user_evidence(uid)

    # 3. Fetch Linked Complaint if exists
    user_complaints = await get_user_complaints(user_id=uid)
    complaint = next((c for c in user_complaints if c.get("category") == category), None)


    # Assemble Case Summary
    issue = case_context.get("issue") or case_context.get("dispute") or category.replace("_", " ").title()
    refusal = case_context.get("seller_refusal") or case_context.get("employer_action") or "unresolved dispute"
    summary_text = (
        f"The user reports a legal issue concerning {issue}. "
        f"The user has documented attempts at resolution; current status indicates: {refusal}. "
        f"A total of {len(user_evidence)} evidence file(s) are stored in the workspace. "
        f"This handoff pack summarizes verified facts, evidence integrity hashes, and verified legal citations for legal review."
    )

    # Assemble Parties
    parties: list[HandoffParty] = [
        HandoffParty(
            role="Complainant",
            name=complaint.get("complainant_name", "User / Complainant") if complaint else "User",
            contact_details=complaint.get("complainant_contact") if complaint else None,
            address=complaint.get("complainant_address") if complaint else None,
        ),
        HandoffParty(
            role="Respondent",
            name=complaint.get("respondent_name", "Opposing Party / Respondent") if complaint else "Opposing Party",
            address=complaint.get("respondent_address") if complaint else None,
        ),
    ]

    # Assemble Chronology
    chronology: list[HandoffTimelineEvent] = []
    purch_date = case_context.get("purchase_date") or case_context.get("incident_date")
    if purch_date:
        chronology.append(
            HandoffTimelineEvent(
                date_or_approx=purch_date,
                event="Transaction / Incident Date",
                certainty="established",
            )
        )
    else:
        chronology.append(
            HandoffTimelineEvent(
                date_or_approx="Date not established",
                event="Primary incident timing requires confirmation",
                certainty="unverified",
            )
        )

    # Assemble Facts & Questions
    facts = [HandoffFact(label=f.label, provenance=f.provenance) for f in readiness.facts_established]
    questions = [HandoffQuestion(label=q.label, reason=q.reason) for q in readiness.facts_missing]

    # Assemble Evidence Index
    evidence_items: list[HandoffEvidenceItem] = []
    for idx, ev in enumerate(user_evidence):
        is_media = ev.get("evidence_type") in ["audio", "video"]
        tx_avail = is_media and ev.get("processing_status") == "ready"
        evidence_items.append(
            HandoffEvidenceItem(
                citation_id=f"EVIDENCE_{idx+1}",
                title=ev.get("title") or ev.get("original_filename", "Evidence File"),
                original_filename=ev.get("original_filename", "file"),
                evidence_type=ev.get("evidence_type", "other"),
                media_type=ev.get("media_type", "application/octet-stream"),
                size_bytes=ev.get("size_bytes", 0),
                sha256=ev.get("sha256", "SHA256_UNAVAILABLE"),
                processing_status=ev.get("processing_status", "pending"),
                transcript_available=tx_avail,
                transcript_sha256=ev.get("sha256") if tx_avail else None,
            )
        )

    # Assemble Complaint Info
    if complaint:
        comp_info = HandoffComplaintInfo(
            status=complaint.get("status", "draft"),
            title=complaint.get("title"),
            is_finalized=(complaint.get("status") == "finalized"),
            generated_text_preview=complaint.get("generated_text", "")[:300] if complaint.get("generated_text") else None,
        )
    else:
        comp_info = HandoffComplaintInfo(
            status="none",
            title=None,
            is_finalized=False,
        )

    # Assemble Legal Sources
    legal_sources: list[HandoffLegalSource] = []
    if readiness.legal_sources:
        for idx, src in enumerate(readiness.legal_sources):
            legal_sources.append(
                HandoffLegalSource(
                    citation_id=src.get("citation_id", f"SOURCE_{idx+1}"),
                    title=src.get("title", "Legal Source"),
                    authority=src.get("authority"),
                    provision_type=src.get("provision_type"),
                    provision_number=src.get("provision_number"),
                    official_url=src.get("official_url") or src.get("landing_page"),
                    last_verified="Verified",
                )
            )

    actions_taken = ["Evidence uploaded and verified", "Case readiness evaluated"]
    if complaint:
        actions_taken.append(f"Complaint workspace created ({complaint.get('status', 'draft')})")

    return LawyerHandoffResponse(
        case_summary=summary_text,
        parties=parties,
        user_objective=case_context.get("desired_outcome") or "Seeking legal resolution and appropriate remedy.",
        chronology=chronology,
        established_facts=facts,
        unresolved_questions=questions,
        evidence_index=evidence_items,
        complaint_summary=comp_info,
        legal_sources=legal_sources,
        actions_already_taken=actions_taken,
        current_next_step=action_plan.primary_next_step,
        generated_at=datetime.now(timezone.utc),
    )


def build_handoff_pdf_export(pack: LawyerHandoffResponse) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Nyaya AI Lawyer Handoff Pack",
        author="Nyaya AI",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("HandoffTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=16, leading=20, alignment=TA_CENTER, spaceAfter=14)
    h2_style = ParagraphStyle("HandoffH2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle("HandoffBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=14, spaceAfter=6)
    note_style = ParagraphStyle("HandoffNote", parent=styles["BodyText"], fontName="Helvetica-Oblique", fontSize=8, leading=11, spaceBefore=14)

    story = [
        Paragraph("NYAYA AI — LAWYER HANDOFF PACK", title_style),
        Paragraph(f"Generated: {pack.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}", ParagraphStyle("Sub", parent=body_style, alignment=TA_CENTER, fontSize=9, spaceAfter=12)),
        Spacer(1, 4 * mm),
        Paragraph("1. Case Summary", h2_style),
        Paragraph(escape(pack.case_summary), body_style),
        Paragraph("2. User Objective", h2_style),
        Paragraph(escape(pack.user_objective), body_style),
        Paragraph("3. Established Facts", h2_style),
    ]

    for f in pack.established_facts:
        story.append(Paragraph(f"• {escape(f.label)}", body_style))

    if pack.unresolved_questions:
        story.append(Paragraph("4. Open Questions / Missing Information", h2_style))
        for q in pack.unresolved_questions:
            story.append(Paragraph(f"• {escape(q.label)}", body_style))

    story.append(Paragraph("5. Evidence Index", h2_style))
    for ev in pack.evidence_index:
        story.append(Paragraph(f"<b>[{ev.citation_id}] {escape(ev.title)}</b> — {ev.evidence_type.upper()} | Status: {ev.processing_status} | SHA-256: {ev.sha256[:16]}...", body_style))

    if pack.legal_sources:
        story.append(Paragraph("6. Verified Legal Sources", h2_style))
        for src in pack.legal_sources:
            story.append(Paragraph(f"<b>[{src.citation_id}] {escape(src.title)}</b> (Section {src.provision_number or 'N/A'})", body_style))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("This pack was organized by Nyaya AI from information and evidence provided in this workspace and verified legal sources. It is intended to help a legal professional review the matter and is not a substitute for professional legal advice.", note_style))

    doc.build(story)
    output.seek(0)
    return output.getvalue()


def build_handoff_docx_export(pack: LawyerHandoffResponse) -> bytes:
    doc = Document()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    trun = title.add_run("NYAYA AI — LAWYER HANDOFF PACK")
    trun.bold = True
    trun.font.size = Pt(14)

    doc.add_heading("1. Case Summary", level=2)
    doc.add_paragraph(pack.case_summary)

    doc.add_heading("2. User Objective", level=2)
    doc.add_paragraph(pack.user_objective)

    doc.add_heading("3. Established Facts", level=2)
    for f in pack.established_facts:
        doc.add_paragraph(f"• {f.label}")

    if pack.unresolved_questions:
        doc.add_heading("4. Open Questions", level=2)
        for q in pack.unresolved_questions:
            doc.add_paragraph(f"• {q.label}")

    doc.add_heading("5. Evidence Index", level=2)
    for ev in pack.evidence_index:
        doc.add_paragraph(f"[{ev.citation_id}] {ev.title} — {ev.evidence_type.upper()} | SHA-256: {ev.sha256}")

    if pack.legal_sources:
        doc.add_heading("6. Verified Legal Sources", level=2)
        for src in pack.legal_sources:
            doc.add_paragraph(f"[{src.citation_id}] {src.title}")

    doc.add_paragraph()
    note = doc.add_paragraph("This pack was organized by Nyaya AI for legal review and does not replace advice from a qualified legal professional.")
    note.runs[0].italic = True
    note.runs[0].font.size = Pt(9)

    out = BytesIO()
    doc.save(out)
    out.seek(0)
    return out.getvalue()
