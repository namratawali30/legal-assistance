from enum import Enum
from typing import Any


class RetrievalMode(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    HYBRID = "HYBRID"
    LIVE_VERIFY = "LIVE_VERIFY"


LIVE_VERIFY_KEYWORDS = [
    "current",
    "amendment",
    "recent notification",
    "latest rule",
    "latest section",
    "latest act",
    "new rule",
    "updated section",
    "latest provision",
    "current law",
    "recent order",
]


def plan_retrieval_strategy(
    question: str,
    category: str | None = None,
    case_context: dict[str, Any] | None = None,
) -> RetrievalMode:
    question_lower = (question or "").lower().strip()

    # 1. Check for explicit live verification triggers
    for kw in LIVE_VERIFY_KEYWORDS:
        if kw in question_lower:
            return RetrievalMode.LIVE_VERIFY

    # 2. General queries in active categories default to HYBRID to enrich answers
    if category in [
        "consumer_rights",
        "labour_rights",
        "womens_safety",
        "educational_rights",
        "anti_ragging",
    ]:
        return RetrievalMode.HYBRID

    return RetrievalMode.LOCAL_ONLY
