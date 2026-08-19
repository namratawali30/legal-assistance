import json
from pathlib import Path
from statistics import mean

from app.rag.retriever import search_legal_chunks


BASE_DIR = Path(__file__).resolve().parents[1]

EVALUATION_PATH = (
    BASE_DIR
    / "knowledge_base"
    / "manifest"
    / "retrieval_evaluation.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "knowledge_base"
    / "manifest"
    / "retrieval_evaluation_results.json"
)


def load_evaluation_queries():
    with EVALUATION_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return data["queries"]


def evaluate_query(query_data):
    results = search_legal_chunks(
        query=query_data["question"],
        top_k=5,
        category=query_data.get("category"),
    )

    scores = [
        result["score"]
        for result in results
    ]

    top_score = (
        scores[0]
        if scores
        else 0.0
    )

    second_score = (
        scores[1]
        if len(scores) > 1
        else 0.0
    )

    average_score = (
        mean(scores)
        if scores
        else 0.0
    )

    margin = (
        top_score - second_score
        if len(scores) > 1
        else top_score
    )

    top_source = (
        results[0]["source_id"]
        if results
        else None
    )

    expected_source = query_data.get(
        "expected_source"
    )

    expected_source_found = False

    if expected_source:
        expected_source_found = any(
            result["source_id"]
            == expected_source
            for result in results
        )

    return {
        "id": query_data["id"],
        "question": query_data["question"],
        "category": query_data.get(
            "category"
        ),
        "supported": query_data[
            "supported"
        ],
        "expected_source":
            expected_source,

        "expected_source_found":
            expected_source_found,

        "top_score":
            round(top_score, 4),

        "second_score":
            round(second_score, 4),

        "average_top5_score":
            round(
                average_score,
                4,
            ),

        "top_margin":
            round(
                margin,
                4,
            ),

        "top_source":
            top_source,

        "top_provision": (
            results[0].get(
                "provision_number"
            )
            if results
            else None
        ),

        "top_provision_title": (
            results[0].get(
                "provision_title"
            )
            if results
            else None
        ),

        "results": [
            {
                "rank": index,
                "score": round(
                    result["score"],
                    4,
                ),
                "source_id":
                    result["source_id"],
                "provision_number":
                    result.get(
                        "provision_number"
                    ),
                "provision_title":
                    result.get(
                        "provision_title"
                    ),
            }
            for index, result in enumerate(
                results,
                start=1,
            )
        ],
    }


def main():
    queries = load_evaluation_queries()

    evaluation_results = []

    print()
    print(
        "Retrieval Confidence Evaluation"
    )
    print("=" * 80)

    for query in queries:
        result = evaluate_query(
            query
        )

        evaluation_results.append(
            result
        )

        label = (
            "SUPPORTED"
            if result["supported"]
            else "UNSUPPORTED"
        )

        print()
        print(
            result["id"],
            f"[{label}]",
        )

        print(
            "Question:",
            result["question"],
        )

        print(
            "Top score:",
            result["top_score"],
        )

        print(
            "Second score:",
            result["second_score"],
        )

        print(
            "Top-5 average:",
            result[
                "average_top5_score"
            ],
        )

        print(
            "Margin:",
            result["top_margin"],
        )

        print(
            "Top source:",
            result["top_source"],
        )

        if result[
            "expected_source"
        ]:
            print(
                "Expected source found:",
                result[
                    "expected_source_found"
                ],
            )

    supported = [
        result
        for result in evaluation_results
        if result["supported"]
    ]

    unsupported = [
        result
        for result in evaluation_results
        if not result["supported"]
    ]

    supported_scores = [
        result["top_score"]
        for result in supported
    ]

    unsupported_scores = [
        result["top_score"]
        for result in unsupported
    ]

    summary = {
        "supported_count":
            len(supported),

        "unsupported_count":
            len(unsupported),

        "supported_top_score_min": (
            min(supported_scores)
            if supported_scores
            else None
        ),

        "supported_top_score_max": (
            max(supported_scores)
            if supported_scores
            else None
        ),

        "supported_top_score_average": (
            round(
                mean(
                    supported_scores
                ),
                4,
            )
            if supported_scores
            else None
        ),

        "unsupported_top_score_min": (
            min(unsupported_scores)
            if unsupported_scores
            else None
        ),

        "unsupported_top_score_max": (
            max(unsupported_scores)
            if unsupported_scores
            else None
        ),

        "unsupported_top_score_average": (
            round(
                mean(
                    unsupported_scores
                ),
                4,
            )
            if unsupported_scores
            else None
        ),
    }

    output = {
        "summary": summary,
        "results":
            evaluation_results,
    }

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for key, value in summary.items():
        print(
            key,
            "=",
            value,
        )

    print()
    print(
        "Results saved to:",
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()