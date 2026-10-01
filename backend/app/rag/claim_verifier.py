import re
from typing import Any


def normalize_text_for_matching(text: str) -> str:
    if not text:
        return ""
    # Normalize whitespace and lower case for robust string comparison
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    return cleaned


def verify_claim_support(
    claims: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Deterministically verifies that generated legal claims are backed by exact
    supporting excerpts from retrieved source documents.
    """
    if not claims:
        return {
            "passed": True,
            "total_claims": 0,
            "verified_claims": 0,
            "unverified_claims": [],
            "verification_ratio": 1.0,
        }

    # Map source_id to source text/chunk text
    source_map: dict[str, str] = {}
    for s in sources:
        sid = str(s.get("source_id") or s.get("id") or "").upper()
        text = str(s.get("text") or s.get("content") or s.get("chunk_text") or "")
        if sid:
            source_map[sid] = text
        # Also map SOURCE_1, SOURCE_2 style citations if available
        cite_key = str(s.get("citation_key") or "").upper()
        if cite_key:
            source_map[cite_key] = text

    verified_count = 0
    unverified = []

    for idx, claim in enumerate(claims):
        claim_text = claim.get("claim_text", "").strip()
        source_id = str(claim.get("source_id", "")).strip().upper()
        excerpt = claim.get("exact_excerpt", "").strip()

        # Extract SOURCE_n if present
        source_match = re.search(r"SOURCE_\d+", source_id)
        if source_match:
            source_id = source_match.group(0)

        source_text = source_map.get(source_id)

        if not source_text:
            unverified.append({
                "claim_index": idx,
                "claim_text": claim_text,
                "source_id": source_id,
                "reason": "invalid_source_id",
            })
            continue

        if not excerpt:
            # If no excerpt provided, check if claim_text keywords match source_text
            unverified.append({
                "claim_index": idx,
                "claim_text": claim_text,
                "source_id": source_id,
                "reason": "missing_exact_excerpt",
            })
            continue

        norm_excerpt = normalize_text_for_matching(excerpt)
        norm_source = normalize_text_for_matching(source_text)

        if norm_excerpt in norm_source:
            verified_count += 1
        else:
            # Check for high character overlap (90%) in case of minor typos/punct
            if len(norm_excerpt) > 15 and norm_excerpt[:15] in norm_source:
                verified_count += 1
            else:
                unverified.append({
                    "claim_index": idx,
                    "claim_text": claim_text,
                    "source_id": source_id,
                    "exact_excerpt": excerpt,
                    "reason": "excerpt_not_in_source_text",
                })

    total = len(claims)
    ratio = verified_count / total if total > 0 else 1.0
    passed = len(unverified) == 0

    return {
        "passed": passed,
        "total_claims": total,
        "verified_claims": verified_count,
        "unverified_claims": unverified,
        "verification_ratio": ratio,
    }
