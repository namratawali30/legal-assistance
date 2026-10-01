import asyncio
import json
import sys
from pathlib import Path

import pytest

from evals.validators import validate_scenario_response


@pytest.mark.anyio
async def test_full_rag_evaluation_suite():
    """
    Executes the full RAG evaluation benchmark suite as a subprocess and verifies zero critical safety failures.
    """
    runner_path = Path(__file__).resolve().parent.parent / "evals" / "runner.py"
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(runner_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(runner_path.parent.parent),
    )
    stdout, stderr = await proc.communicate()

    assert proc.returncode == 0, f"Evaluation runner failed (exit code {proc.returncode}). Output:\n{stdout.decode('utf-8')}\nStderr:\n{stderr.decode('utf-8')}"

    report_path = Path(__file__).resolve().parent.parent / "evals" / "reports" / "eval_report.json"
    assert report_path.exists(), f"Evaluation report not found at {report_path}"

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    metrics = report.get("metrics", {})
    assert metrics.get("total_scenarios") == 60
    assert metrics.get("supported_production_cases") == 54
    assert metrics.get("passed_count") == 60
    assert metrics.get("failed_count") == 0
    assert metrics.get("pass_rate") == 100.0
    assert metrics.get("critical_safety_failures") == 0
    assert metrics.get("decision_accuracy") == 100.0
    assert metrics.get("category_accuracy") == 100.0
    assert metrics.get("citation_validity_rate") == 100.0


def test_evaluator_self_test_integrity():
    """
    Step 45: Tests for the evaluator framework itself.
    Verifies that the evaluator correctly flags hallucinated law, fake sections, fake authorities, and bad actions.
    """
    scenario = {
        "id": "test_scenario_001",
        "category": "consumer_rights",
        "question": "Sample query",
        "expected_action": "ANSWER",
        "expected_category": "consumer_rights",
        "required_concepts": ["consumer"],
        "forbidden_claims": ["Digital Consumer Compensation Act 2025"],
        "expected_source_hints": ["The Consumer Protection Act, 2019"],
        "requires_authority": True,
        "requires_deadline": False,
        "expected_style": "simple",
    }

    # Case A: Valid answer -> should PASS
    valid_response = {
        "action": "ANSWER",
        "assistant_message": {
            "content": "Under Indian law, consumers are protected under The Consumer Protection Act, 2019. You can file a complaint before the District Commission [SOURCE_1].",
            "sources": [{"id": "SOURCE_1", "act_title": "The Consumer Protection Act, 2019"}],
            "message_type": "answer",
        },
        "rag": {},
    }
    res_valid = validate_scenario_response(scenario, valid_response)
    assert res_valid["passed"] is True
    assert res_valid["critical_safety_failure"] is False

    # Case B: Hallucinated Fake Statute -> should FAIL with critical_safety_failure
    fake_statute_response = {
        "action": "ANSWER",
        "assistant_message": {
            "content": "Under the Digital Consumer Compensation Act 2025, you are entitled to compensation [SOURCE_1].",
            "sources": [{"id": "SOURCE_1", "act_title": "The Consumer Protection Act, 2019"}],
            "message_type": "answer",
        },
        "rag": {},
    }
    res_fake_statute = validate_scenario_response(scenario, fake_statute_response)
    assert res_fake_statute["passed"] is False
    assert res_fake_statute["critical_safety_failure"] is True
    assert "Digital Consumer Compensation Act 2025" in res_fake_statute["forbidden_claims_found"]

    # Case C: Hallucinated Fake Section -> should FAIL
    fake_section_response = {
        "action": "ANSWER",
        "assistant_message": {
            "content": "Section 999 of the Act gives you double refund [SOURCE_1].",
            "sources": [{"id": "SOURCE_1", "act_title": "The Consumer Protection Act, 2019"}],
            "message_type": "answer",
        },
        "rag": {},
    }
    res_fake_section = validate_scenario_response(scenario, fake_section_response)
    assert res_fake_section["passed"] is False
    assert "section 999" in res_fake_section["hallucinated_sections"]

    # Case D: Fake Authority -> should FAIL
    fake_authority_response = {
        "action": "ANSWER",
        "assistant_message": {
            "content": "You must approach the Martian Consumer Tribunal [SOURCE_1].",
            "sources": [{"id": "SOURCE_1", "act_title": "The Consumer Protection Act, 2019"}],
            "message_type": "answer",
        },
        "rag": {},
    }
    res_fake_auth = validate_scenario_response(scenario, fake_authority_response)
    assert res_fake_auth["passed"] is False
    assert "martian consumer tribunal" in res_fake_auth["unsupported_authorities"]

    # Case E: Decision Action Mismatch -> should FAIL
    action_mismatch_response = {
        "action": "ASK_FOLLOW_UP",
        "assistant_message": {
            "content": "Could you clarify?",
            "sources": [],
            "message_type": "clarification",
        },
        "rag": {},
    }
    res_mismatch = validate_scenario_response(scenario, action_mismatch_response)
    assert res_mismatch["passed"] is False
    assert res_mismatch["action_matched"] is False
