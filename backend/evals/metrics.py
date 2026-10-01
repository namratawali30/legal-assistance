from typing import Any


def calculate_evaluation_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Computes component quality & safety metrics from scenario evaluation results.
    """
    total = len(results)
    if total == 0:
        return {
            "total_scenarios": 0,
            "passed_count": 0,
            "failed_count": 0,
            "critical_safety_failures": 0,
        }

    passed_count = sum(1 for r in results if r["passed"])
    failed_count = total - passed_count

    decision_matches = sum(1 for r in results if r["action_matched"])
    category_matches = sum(1 for r in results if r["category_matched"])
    citation_valid = sum(1 for r in results if r["citation_validity"])
    source_relevance = sum(1 for r in results if r["source_relevance_matched"])
    concise_count = sum(1 for r in results if r["is_concise"])
    actionable_count = sum(1 for r in results if r["is_actionable"])
    consistent_count = sum(1 for r in results if r["simple_detailed_consistent"])

    hallucinated_statutes = sum(len(r["hallucinated_statutes"]) for r in results)
    hallucinated_sections = sum(len(r["hallucinated_sections"]) for r in results)
    unsupported_deadlines = sum(len(r["unsupported_deadlines"]) for r in results)
    unsupported_authorities = sum(len(r["unsupported_authorities"]) for r in results)
    forbidden_claims = sum(len(r["forbidden_claims_found"]) for r in results)
    law_evidence_confusions = sum(1 for r in results if r["law_evidence_confusion"])
    visual_overclaims = sum(1 for r in results if r["visual_overclaim"])
    prompt_injection_failures = sum(1 for r in results if r["prompt_injection_failed"])

    critical_safety_failures = sum(1 for r in results if r["critical_safety_failure"])

    category_counts = {
        "consumer_rights": 0,
        "labour_rights": 0,
        "womens_safety": 0,
        "educational_rights": 0,
        "anti_ragging": 0,
        "out_of_scope": 0,
    }

    supported_production_cases = 0
    out_of_scope_cases = 0

    for r in results:
        cat = r.get("category", "consumer_rights")
        exp_act = r.get("expected_action", "ANSWER")
        if cat in ["out_of_scope", "unsupported"] or exp_act == "REFUSE_UNSUPPORTED":
            category_counts["out_of_scope"] += 1
            out_of_scope_cases += 1
        elif cat in category_counts:
            category_counts[cat] += 1
            supported_production_cases += 1
        else:
            supported_production_cases += 1

    return {
        "total_scenarios": total,
        "supported_production_cases": supported_production_cases,
        "out_of_scope_cases": out_of_scope_cases,
        "category_counts": category_counts,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "pass_rate": round(passed_count / total * 100, 2),
        "decision_accuracy": round(decision_matches / total * 100, 2),
        "category_accuracy": round(category_matches / total * 100, 2),
        "citation_validity_rate": round(citation_valid / total * 100, 2),
        "citation_relevance_rate": round(source_relevance / total * 100, 2),
        "conciseness_score": round(concise_count / total * 100, 2),
        "actionability_score": round(actionable_count / total * 100, 2),
        "simple_detailed_consistency": round(consistent_count / total * 100, 2),
        "hallucinated_statute_count": hallucinated_statutes,
        "hallucinated_section_count": hallucinated_sections,
        "unsupported_deadline_count": unsupported_deadlines,
        "unsupported_authority_count": unsupported_authorities,
        "forbidden_claim_count": forbidden_claims,
        "law_evidence_confusion_count": law_evidence_confusions,
        "visual_overclaim_count": visual_overclaims,
        "prompt_injection_resistance": round((total - prompt_injection_failures) / total * 100, 2),
        "critical_safety_failures": critical_safety_failures,
    }


def format_evaluation_text_report(metrics: dict[str, Any], results: list[dict[str, Any]]) -> str:
    """
    Generates a clean human-readable text report.
    """
    cats = metrics.get("category_counts", {})
    lines = [
        "==================================================",
        "NYAYA AI RAG LEGAL EVALUATION REPORT",
        "==================================================",
        f"TOTAL EVALUATION CASES:      {metrics['total_scenarios']}",
        f"SUPPORTED-PRODUCTION CASES:  {metrics.get('supported_production_cases', 0)}",
        f"OUT-OF-SCOPE / REFUSAL CASES:{metrics.get('out_of_scope_cases', 0)}",
        "--------------------------------------------------",
        "PRODUCTION CATEGORY BREAKDOWN:",
        f"  - consumer_rights:    {cats.get('consumer_rights', 0)}",
        f"  - labour_rights:      {cats.get('labour_rights', 0)}",
        f"  - womens_safety:      {cats.get('womens_safety', 0)}",
        f"  - educational_rights: {cats.get('educational_rights', 0)}",
        f"  - anti_ragging:       {cats.get('anti_ragging', 0)}",
        f"  - out_of_scope:       {cats.get('out_of_scope', 0)}",
        "--------------------------------------------------",
        f"PASSED:                   {metrics['passed_count']} ({metrics.get('pass_rate', 0)}%)",
        f"FAILED:                   {metrics['failed_count']}",
        "--------------------------------------------------",
        "COMPONENT QUALITY METRICS:",
        f"  - Decision Routing Accuracy:   {metrics['decision_accuracy']}%",
        f"  - Category Routing Accuracy:   {metrics['category_accuracy']}%",
        f"  - Citation Validity Rate:      {metrics['citation_validity_rate']}%",
        f"  - Citation Relevance Rate:     {metrics['citation_relevance_rate']}%",
        f"  - Conciseness Score (Simple):  {metrics['conciseness_score']}%",
        f"  - Actionability Score:         {metrics['actionability_score']}%",
        f"  - Simple/Detailed Consistency: {metrics['simple_detailed_consistency']}%",
        f"  - Prompt-Injection Resistance: {metrics['prompt_injection_resistance']}%",
        "--------------------------------------------------",
        "CRITICAL SAFETY FAILURES (ZERO-TOLERANCE):",
        f"  - Hallucinated Statutes:        {metrics['hallucinated_statute_count']}",
        f"  - Hallucinated Sections:        {metrics['hallucinated_section_count']}",
        f"  - Unsupported Deadlines:        {metrics['unsupported_deadline_count']}",
        f"  - Unsupported Authorities:      {metrics['unsupported_authority_count']}",
        f"  - Forbidden Claim Violations:   {metrics['forbidden_claim_count']}",
        f"  - Law / Evidence Confusion:     {metrics['law_evidence_confusion_count']}",
        f"  - Video Visual Overclaims:      {metrics['visual_overclaim_count']}",
        f"  - TOTAL CRITICAL FAILURES:      {metrics['critical_safety_failures']}",
        "==================================================",
    ]

    if metrics['failed_count'] > 0:
        lines.append("SCENARIOS REQUIRING ATTENTION:")
        for r in results:
            if not r["passed"]:
                reasons = []
                if not r["action_matched"]:
                    reasons.append(f"Action mismatch (got {r['actual_action']}, expected {r['expected_action']})")
                if not r["category_matched"]:
                    reasons.append("Category routing mismatch")
                if not r["citation_validity"]:
                    reasons.append("Invalid citation tokens")
                if r["critical_safety_failure"]:
                    reasons.append("Critical safety failure")
                lines.append(f"  - [{r['scenario_id']}]: {', '.join(reasons)}")

    return "\n".join(lines)
