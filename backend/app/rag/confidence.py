from typing import Any


DEFAULT_MIN_RELEVANCE_SCORE = 0.45


def evaluate_retrieval_confidence(
    results: list[dict[str, Any]],
    min_score: float = DEFAULT_MIN_RELEVANCE_SCORE,
) -> dict[str, Any]:
    if not results:
        return {
            "accepted": False,
            "reason": "no_results",
            "top_score": 0.0,
            "threshold": min_score,
        }

    top_score = float(
        results[0].get(
            "score",
            0.0,
        )
    )

    if top_score < min_score:
        return {
            "accepted": False,
            "reason": "low_relevance",
            "top_score": top_score,
            "threshold": min_score,
        }

    return {
        "accepted": True,
        "reason": "sufficient_relevance",
        "top_score": top_score,
        "threshold": min_score,
    }