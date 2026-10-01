import logging
from typing import Any
from bson import ObjectId

from app.schemas.readiness import (
    CaseReadinessResponse,
    CaseReadinessState,
    EvidenceAvailableItem,
    EvidenceGapItem,
    FactEstablished,
    FactMissing,
)
from app.database import database


logger = logging.getLogger(__name__)

AUTHORITY_MAP = {
    "consumer_rights": "District Consumer Disputes Redressal Commission",
    "labour_rights": "Office of the Labour Commissioner / Labour Court",
    "womens_safety": "Internal Committee (IC) / Local Complaints Committee (LCC) / Police",
    "educational_rights": "Educational Board / University Grievance Redressal Committee",
    "anti_ragging": "Anti-Ragging Committee / Head of Institution / UGC Helpline",
}


async def compute_session_readiness(
    session: dict[str, Any],
    user_id: ObjectId | str,
) -> CaseReadinessResponse:
    db = database
    uid = ObjectId(user_id) if isinstance(user_id, str) else user_id
    category = session.get("category", "consumer_rights")
    case_context = session.get("case_context", {}) or {}

    # 1. Fetch user's evidence records
    evidence_cursor = db.evidence_vault.find({"user_id": uid})
    user_evidence = await evidence_cursor.to_list(length=100)

    # 2. Evaluate Established Facts from context
    facts_established: list[FactEstablished] = []
    facts_missing: list[FactMissing] = []

    # Common facts check
    if case_context.get("issue") or case_context.get("dispute") or case_context.get("relationship"):
        facts_established.append(
            FactEstablished(
                label=f"Core dispute area identified ({category.replace('_', ' ').title()})",
                status="established",
                provenance=["chat_context"],
            )
        )

    if case_context.get("purchase_date") or case_context.get("incident_date"):
        facts_established.append(
            FactEstablished(
                label="Date of incident / transaction documented",
                status="established",
                provenance=["chat_context"],
            )
        )
    else:
        facts_missing.append(
            FactMissing(
                label="Approximate date of incident or transaction",
                importance="high",
                reason="Important for determining limitation and timelines.",
            )
        )

    if case_context.get("location") or case_context.get("incident_location"):
        facts_established.append(
            FactEstablished(
                label="Location / Jurisdiction documented",
                status="established",
                provenance=["chat_context"],
            )
        )
    else:
        facts_missing.append(
            FactMissing(
                label="Location / State where incident occurred",
                importance="medium",
                reason="Needed to identify local authority jurisdiction.",
            )
        )

    if case_context.get("seller_refusal") or case_context.get("threats_or_coercion") or case_context.get("respondent_name"):
        facts_established.append(
            FactEstablished(
                label="Opposing party response / conduct noted",
                status="established",
                provenance=["chat_context"],
            )
        )

    # Category specific checks
    if category == "anti_ragging":
        if case_context.get("institution_type") == "college" or "college" in str(case_context).lower():
            facts_established.append(
                FactEstablished(
                    label="Educational institution context established",
                    status="established",
                    provenance=["chat_context"],
                )
            )
        else:
            facts_missing.append(
                FactMissing(
                    label="Confirmation of educational institution",
                    importance="high",
                    reason="Required to apply UGC Anti-Ragging regulations.",
                )
            )

    # 3. Evaluate Evidence Items
    evidence_available: list[EvidenceAvailableItem] = []
    ready_evidence_count = 0

    for ev in user_evidence:
        status = ev.get("status", "pending")
        title = ev.get("title") or ev.get("original_filename") or "Evidence File"
        supports_text = None

        if status == "ready":
            ready_evidence_count += 1
            supports_text = "Extracted text verified & available for complaint grounding"
        elif status == "requires_ocr":
            supports_text = "File stored securely; OCR text extraction pending"
        elif status in ["no_text", "failed"]:
            supports_text = "File stored; no readable text extracted"
        else:
            supports_text = "File uploaded; processing in progress"

        evidence_available.append(
            EvidenceAvailableItem(
                evidence_id=str(ev["_id"]),
                title=title,
                status=status,
                supports=supports_text,
            )
        )

    # 4. Evaluate Evidence Gaps conservatively
    evidence_gaps: list[EvidenceGapItem] = []
    if ready_evidence_count == 0:
        evidence_gaps.append(
            EvidenceGapItem(
                label="Supporting documentation (Invoice / Communication / Proof)",
                recommendation="Uploading receipts, notices, or messages will strengthen your complaint drafting.",
            )
        )
    elif category == "consumer_rights" and ready_evidence_count == 1:
        evidence_gaps.append(
            EvidenceGapItem(
                label="Proof of payment / Written refusal",
                recommendation="Adding payment receipts or written refusal messages could help document the dispute.",
            )
        )

    # 5. Grounded Legal Sources from session history (if assistant messages contain sources)
    legal_sources: list[dict[str, Any]] = []

    # 6. Determine Possible Authority
    possible_authority = AUTHORITY_MAP.get(category)
    if facts_missing and any(f.importance == "high" for f in facts_missing):
        # If critical high-importance facts are missing, authority remains tentative
        possible_authority = f"{possible_authority} (Pending location/factual details)" if possible_authority else None

    # 7. Calculate Readiness State & Next Step
    if facts_missing and any(f.importance == "high" for f in facts_missing):
        readiness_state = CaseReadinessState.NEEDS_INFORMATION
        next_step = f"Clarify remaining details: {facts_missing[0].label.lower()}."
    elif ready_evidence_count == 0 and len(user_evidence) == 0:
        readiness_state = CaseReadinessState.NEEDS_EVIDENCE
        next_step = "Upload supporting documents (invoices, receipts, or messages) to the Evidence Vault."
    else:
        readiness_state = CaseReadinessState.READY_FOR_NEXT_STEP
        next_step = "You appear to have sufficient information to prepare a formal legal complaint draft."

    return CaseReadinessResponse(
        readiness_state=readiness_state,
        facts_established=facts_established,
        facts_missing=facts_missing,
        evidence_available=evidence_available,
        evidence_gaps=evidence_gaps,
        legal_sources=legal_sources,
        possible_authority=possible_authority,
        next_step=next_step,
    )


async def compute_complaint_readiness(
    complaint: dict[str, Any],
    user_id: ObjectId | str,
) -> CaseReadinessResponse:
    db = database
    uid = ObjectId(user_id) if isinstance(user_id, str) else user_id
    category = complaint.get("category", "consumer_rights")

    # 1. Fetch user's evidence records
    evidence_cursor = db.evidence_vault.find({"user_id": uid})
    user_evidence = await evidence_cursor.to_list(length=100)

    facts_established: list[FactEstablished] = []
    facts_missing: list[FactMissing] = []

    # Established from complaint fields
    if complaint.get("complainant_name") and complaint.get("respondent_name"):
        facts_established.append(
            FactEstablished(
                label=f"Parties identified ({complaint['complainant_name']} vs {complaint['respondent_name']})",
                status="established",
                provenance=["complaint_fields"],
            )
        )
    else:
        facts_missing.append(
            FactMissing(
                label="Full names of complainant or respondent",
                importance="high",
                reason="Required for filing legal complaints.",
            )
        )

    if complaint.get("facts") and len(complaint["facts"]) >= 20:
        facts_established.append(
            FactEstablished(
                label="Factual narrative provided",
                status="established",
                provenance=["complaint_facts"],
            )
        )

    if complaint.get("incident_date"):
        facts_established.append(
            FactEstablished(
                label=f"Incident date specified ({complaint['incident_date']})",
                status="established",
                provenance=["complaint_date"],
            )
        )
    else:
        facts_missing.append(
            FactMissing(
                label="Incident date",
                importance="high",
                reason="Required to establish cause of action timeline.",
            )
        )

    if complaint.get("incident_location"):
        facts_established.append(
            FactEstablished(
                label=f"Incident location specified ({complaint['incident_location']})",
                status="established",
                provenance=["complaint_location"],
            )
        )
    else:
        facts_missing.append(
            FactMissing(
                label="Incident location / State",
                importance="medium",
                reason="Needed for jurisdictional filing.",
            )
        )

    # Evidence status
    evidence_available: list[EvidenceAvailableItem] = []
    ready_count = 0

    ev_refs = complaint.get("evidence_references", [])
    ref_ids = {str(ref["evidence_id"]) for ref in ev_refs if "evidence_id" in ref}

    for ev in user_evidence:
        ev_id = str(ev["_id"])
        is_linked = ev_id in ref_ids
        status = ev.get("status", "pending")
        title = ev.get("title") or ev.get("original_filename") or "Evidence File"

        if is_linked:
            supports = "Linked to this complaint"
            if status == "ready":
                ready_count += 1
            elif status == "requires_ocr":
                supports += " (OCR pending)"
            evidence_available.append(
                EvidenceAvailableItem(
                    evidence_id=ev_id,
                    title=title,
                    status=status,
                    supports=supports,
                )
            )

    evidence_gaps: list[EvidenceGapItem] = []
    if ready_count == 0:
        evidence_gaps.append(
            EvidenceGapItem(
                label="Linked verified evidence",
                recommendation="Linking processed evidence documents to this complaint will strengthen factual grounding.",
            )
        )

    possible_authority = AUTHORITY_MAP.get(category)
    sources = complaint.get("sources", [])
    legal_sources = [s for s in sources if isinstance(s, dict)]

    if facts_missing and any(f.importance == "high" for f in facts_missing):
        readiness_state = CaseReadinessState.NEEDS_INFORMATION
        next_step = f"Complete missing details: {facts_missing[0].label.lower()}."
    elif ready_count == 0:
        readiness_state = CaseReadinessState.NEEDS_EVIDENCE
        next_step = "Link ready evidence documents to support your complaint narrative."
    else:
        readiness_state = CaseReadinessState.READY_FOR_NEXT_STEP
        next_step = "Your complaint has established facts and linked evidence ready for finalization/export."

    return CaseReadinessResponse(
        readiness_state=readiness_state,
        facts_established=facts_established,
        facts_missing=facts_missing,
        evidence_available=evidence_available,
        evidence_gaps=evidence_gaps,
        legal_sources=legal_sources,
        possible_authority=possible_authority,
        next_step=next_step,
    )
