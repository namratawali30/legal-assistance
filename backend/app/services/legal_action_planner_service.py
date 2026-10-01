import logging
from typing import Any
from bson import ObjectId

from app.database import database
from app.schemas.action_plan import (
    ActionPlanResponse,
    ActionStep,
    ActionStepState,
    PlanStatus,
)
from app.schemas.readiness import CaseReadinessState
from app.services.case_readiness_service import (
    compute_complaint_readiness,
    compute_session_readiness,
)

logger = logging.getLogger(__name__)


async def generate_session_action_plan(
    session: dict[str, Any],
    user_id: ObjectId | str,
) -> ActionPlanResponse:
    uid = ObjectId(user_id) if isinstance(user_id, str) else user_id
    category = session.get("category", "consumer_rights")
    case_context = session.get("case_context", {}) or {}

    # 1. Get Case Readiness evaluation
    readiness = await compute_session_readiness(session, user_id)

    steps: list[ActionStep] = []
    caution: str | None = None

    # Safety Context Check (Anti-Ragging / Coercion)
    has_threats = (
        category == "anti_ragging"
        or case_context.get("threats_or_coercion")
        or "threat" in str(case_context).lower()
    )

    if has_threats:
        steps.append(
            ActionStep(
                order=1,
                title="Prioritize Personal Safety & Contact Anti-Ragging Authorities",
                instruction="If you are experiencing active intimidation or physical threats, inform college authorities or call the National Anti-Ragging Helpline (1800-180-5522) immediately.",
                reason="Physical safety and psychological well-being take immediate priority over administrative complaints.",
                priority="high",
            )
        )
        caution = "If you are in immediate physical danger, contact emergency services or institutional security first."

    # Handle readiness states
    if readiness.readiness_state == CaseReadinessState.NEEDS_INFORMATION:
        missing_label = readiness.facts_missing[0].label if readiness.facts_missing else "key case facts"
        steps.append(
            ActionStep(
                order=len(steps) + 1,
                title=f"Clarify Missing Information: {missing_label}",
                instruction=f"Answer the follow-up clarification regarding {missing_label.lower()} to enable legal grounding.",
                reason="Essential context is required to determine exact applicable rules and authority.",
                priority="high",
            )
        )
        return ActionPlanResponse(
            status=PlanStatus.NEEDS_MORE_INFORMATION,
            steps=steps,
            primary_next_step=f"Clarify: {missing_label}.",
            important_caution=caution,
        )

    # 2. Add Evidence Preservation / Upload Step
    if readiness.evidence_available:
        ready_ev = [ev for ev in readiness.evidence_available if ev.status == "ready"]
        ocr_ev = [ev for ev in readiness.evidence_available if ev.status == "requires_ocr"]

        if ready_ev:
            ev_citations = [f"EVIDENCE_{idx+1}" for idx in range(len(ready_ev))]
            steps.append(
                ActionStep(
                    order=len(steps) + 1,
                    title="Preserve Existing Documentation",
                    instruction="Keep original digital copies and unedited screenshots of invoices and seller communication safe.",
                    reason="Preserving original records ensures evidentiary integrity.",
                    evidence_citations=ev_citations,
                    priority="high",
                    state=ActionStepState.DONE,
                )
            )

        if ocr_ev:
            steps.append(
                ActionStep(
                    order=len(steps) + 1,
                    title="Complete OCR Text Extraction for Image Evidence",
                    instruction=f"Processed text for {ocr_ev[0].title} is pending OCR text extraction.",
                    reason="Extracting text ensures facts can be automatically verified in complaint drafting.",
                    priority="medium",
                )
            )
    else:
        steps.append(
            ActionStep(
                order=len(steps) + 1,
                title="Gather & Upload Supporting Documents",
                instruction="Upload receipts, invoices, or messages to the Evidence Vault.",
                reason="Documentary proof strengthens the factual basis of your complaint.",
                priority="high",
            )
        )

    # 3. Add Written Notice / Communication Step
    if category == "consumer_rights":
        steps.append(
            ActionStep(
                order=len(steps) + 1,
                title="Issue Written Notice / Complaint to Seller",
                instruction="State the defect, requested remedy (refund/replacement), and set a reasonable response window.",
                reason="Filing a direct written complaint establishes seller refusal before escalation.",
                priority="medium",
            )
        )
    elif category == "labour_rights":
        steps.append(
            ActionStep(
                order=len(steps) + 1,
                title="Submit Formal Internal Grievance to Employer / HR",
                instruction="Document the grievance in writing to employer or Internal Complaints Committee.",
                reason="Establishing internal escalation attempts is necessary for statutory labour recourse.",
                priority="medium",
            )
        )

    # 4. Add Complaint Workspace Step
    steps.append(
        ActionStep(
            order=len(steps) + 1,
            title="Prepare Structured Legal Complaint Draft",
            instruction="Use the Complaint Workspace to generate a structured complaint grounded in verified law and evidence.",
            reason="Generates a formal legal petition ready for submission to the appropriate commission/authority.",
            source_citations=["SOURCE_1"] if readiness.legal_sources else [],
            priority="high",
        )
    )

    primary_next = steps[0].instruction if steps else "Review your case context."

    return ActionPlanResponse(
        status=PlanStatus.PLAN_AVAILABLE,
        steps=steps[:5],  # Enforce 3–5 focused steps contract
        primary_next_step=readiness.next_step or primary_next,
        important_caution=caution,
    )


async def generate_complaint_action_plan(
    complaint: dict[str, Any],
    user_id: ObjectId | str,
) -> ActionPlanResponse:
    uid = ObjectId(user_id) if isinstance(user_id, str) else user_id
    status = complaint.get("status", "draft")
    category = complaint.get("category", "consumer_rights")

    readiness = await compute_complaint_readiness(complaint, user_id)
    steps: list[ActionStep] = []

    if status == "finalized":
        steps.append(
            ActionStep(
                order=1,
                title="Download Finalized Complaint & Attachments",
                instruction="Export your finalized complaint document in PDF or DOCX format.",
                reason="Your complaint is finalized and locked against modification.",
                priority="high",
                state=ActionStepState.DONE,
            )
        )
        steps.append(
            ActionStep(
                order=2,
                title="Submit to Appropriate Commission / Authority",
                instruction=f"File the finalized complaint before the {readiness.possible_authority or 'appropriate commission'}.",
                reason="Official filing initiates legal proceedings.",
                source_citations=["SOURCE_1"] if complaint.get("sources") else [],
                priority="high",
            )
        )
        return ActionPlanResponse(
            status=PlanStatus.PLAN_AVAILABLE,
            steps=steps,
            primary_next_step="Export your finalized complaint and submit it to the appropriate commission.",
            important_caution="Finalized complaints are locked against further edits.",
        )

    if status in ["generated", "edited"]:
        steps.append(
            ActionStep(
                order=1,
                title="Review & Verify Complaint Draft Details",
                instruction="Carefully review the generated facts and relief requested in the Complaint Workspace.",
                reason="Verifying accuracy ensures all claims match your evidence.",
                priority="high",
            )
        )
        steps.append(
            ActionStep(
                order=2,
                title="Finalize Complaint for Export",
                instruction="Click 'Finalize Complaint' when satisfied with the draft.",
                reason="Finalization locks the document for PDF/DOCX download.",
                priority="high",
            )
        )
        return ActionPlanResponse(
            status=PlanStatus.PLAN_AVAILABLE,
            steps=steps,
            primary_next_step="Review the generated complaint text and finalize when ready.",
        )

    # Draft status
    steps.append(
        ActionStep(
            order=1,
            title="Link Processed Evidence to Complaint",
            instruction="Attach ready evidence documents from Evidence Vault to support your factual claims.",
            reason="Linked evidence is cited directly inside the generated complaint narrative.",
            priority="high",
        )
    )
    steps.append(
        ActionStep(
            order=2,
            title="Generate AI Grounded Complaint Draft",
            instruction="Click 'Generate Complaint' to produce a formal petition grounded in verified law and evidence.",
            reason="Converts your facts and linked evidence into a formal legal draft.",
            priority="high",
        )
    )

    return ActionPlanResponse(
        status=PlanStatus.PLAN_AVAILABLE,
        steps=steps,
        primary_next_step="Link processed evidence files and click 'Generate Complaint'.",
    )
