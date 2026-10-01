import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure backend directory is on PYTHONPATH
evals_dir = Path(__file__).resolve().parent
backend_dir = evals_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.rag.llm_client import generate_text
from app.services.chat_service import create_legal_chat_turn, create_session
from evals.metrics import calculate_evaluation_metrics, format_evaluation_text_report
from evals.validators import validate_scenario_response


async def run_scenario_evaluation(scenario: dict[str, Any], user_id: str = "eval_test_user") -> dict[str, Any]:
    """
    Executes a single synthetic evaluation scenario through the legal RAG turn pipeline.
    """
    scenario_id = scenario["id"]
    category = scenario.get("category", "consumer_rights")
    question = scenario["question"]
    case_context = scenario.get("case_context", {})
    expected_action = scenario.get("expected_action", "ANSWER")

    # Create temporary session object or run evaluation turn
    session = await create_session(
        user_id=user_id,
        title=f"Eval Session {scenario_id}",
        category=category,
        answer_mode="simple",
    )

    session_id = session["_id"]

    # Execute Simple mode turn
    turn_result = await create_legal_chat_turn(
        session_id=session_id,
        user_id=user_id,
        content=question,
        answer_mode="simple",
    )

    if not turn_result:
        return {
            "scenario_id": scenario_id,
            "passed": False,
            "error": "Failed to create legal chat turn",
            "action_matched": False,
            "actual_action": "ERROR",
            "expected_action": expected_action,
            "category_matched": False,
            "citation_validity": False,
            "source_relevance_matched": False,
            "concepts_covered": False,
            "is_concise": True,
            "is_actionable": False,
            "simple_detailed_consistent": True,
            "hallucinated_statutes": [],
            "hallucinated_sections": [],
            "unsupported_deadlines": [],
            "unsupported_authorities": [],
            "forbidden_claims_found": [],
            "law_evidence_confusion": False,
            "visual_overclaim": False,
            "prompt_injection_failed": False,
            "critical_safety_failure": True,
            "word_count": 0,
        }

    # Execute Detailed mode turn if simple mode produced an answer
    detailed_turn_result = None
    if turn_result.get("assistant_message", {}).get("message_type") == "answer":
        detailed_session = await create_session(
            user_id=user_id,
            title=f"Eval Session Detailed {scenario_id}",
            category=category,
            answer_mode="detailed",
        )
        detailed_turn_result = await create_legal_chat_turn(
            session_id=detailed_session["_id"],
            user_id=user_id,
            content=question,
            answer_mode="detailed",
        )

    # Validate response
    validation_res = validate_scenario_response(
        scenario=scenario,
        turn_response=turn_result,
        detailed_turn_response=detailed_turn_result,
    )

    return validation_res


async def run_evaluation_suite(dataset_path: Path | None = None) -> tuple[int, dict[str, Any], list[dict[str, Any]]]:
    """
    Runs full synthetic RAG evaluation suite.
    """
    if dataset_path is None:
        dataset_path = evals_dir / "dataset.json"

    if not dataset_path.exists():
        print(f"Error: Evaluation dataset file not found at {dataset_path}")
        return 1, {}, []

    with dataset_path.open("r", encoding="utf-8") as f:
        dataset = json.load(f)

    # Force mock LLM provider mode for deterministic core evaluation unless RUN_LIVE_MODEL_EVAL=1 is set
    original_llm_key = settings.llm_api_key
    if not os.environ.get("RUN_LIVE_MODEL_EVAL"):
        settings.llm_api_key = "mock"
        # Mock search_india_code to return [] during offline evals to prevent network timeouts
        from app.services import india_code_retriever

        async def _mock_search_india_code(query: str, max_results: int = 5):
            return []

        india_code_retriever.search_india_code = _mock_search_india_code

    results = []
    print(f"Executing Nyaya AI RAG Evaluation Suite on {len(dataset)} synthetic scenarios...")
    for idx, scenario in enumerate(dataset, 1):
        print(f"  [{idx}/{len(dataset)}] Evaluating scenario '{scenario['id']}' ({scenario.get('category')})...")
        res = await run_scenario_evaluation(scenario)
        results.append(res)

    # Calculate metrics
    metrics = calculate_evaluation_metrics(results)
    text_report = format_evaluation_text_report(metrics, results)

    # Print report
    print("\n" + text_report)

    # Save machine-readable JSON report
    reports_dir = evals_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / "eval_report.json"

    with report_file.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "metrics": metrics,
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\nSaved machine-readable report to {report_file}")

    # Determine exit code: 0 if 0 critical safety failures and 100% pass rate in deterministic mode
    exit_code = 0
    if metrics["critical_safety_failures"] > 0 or metrics["passed_count"] < metrics["total_scenarios"]:
        exit_code = 1

    return exit_code, metrics, results


def main():
    exit_code, _, _ = asyncio.run(run_evaluation_suite())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
