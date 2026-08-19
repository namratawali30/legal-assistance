import asyncio
import inspect
from pathlib import Path

import faiss

from app.main import app
from app.rag.answer_generator import generate_legal_answer
from app.rag.confidence import evaluate_retrieval_confidence
from app.rag.conversation import build_conversation_query
from app.rag.retriever import search_legal_chunks
from app.services.chat_service import (
    create_legal_chat_turn,
    retry_failed_assistant_message,
)


BASE_DIR = Path(__file__).resolve().parents[1]

VECTOR_INDEX_PATH = (
    BASE_DIR
    / "knowledge_base"
    / "vector_store"
    / "legal.index"
)


def print_result(
    name: str,
    passed: bool,
    detail: str = "",
):
    status = "PASS" if passed else "FAIL"

    print(
        f"[{status}] {name}"
        + (
            f" — {detail}"
            if detail
            else ""
        )
    )


def test_vector_store():
    if not VECTOR_INDEX_PATH.exists():
        print_result(
            "FAISS index exists",
            False,
            str(VECTOR_INDEX_PATH),
        )
        return False

    index = faiss.read_index(
        str(VECTOR_INDEX_PATH)
    )

    valid = (
        index.ntotal == 331
        and index.d == 384
    )

    print_result(
        "FAISS vector store",
        valid,
        (
            f"vectors={index.ntotal}, "
            f"dimension={index.d}"
        ),
    )

    return valid


def test_async_functions():
    rag_async = inspect.iscoroutinefunction(
        generate_legal_answer
    )

    chat_async = inspect.iscoroutinefunction(
        create_legal_chat_turn
    )

    retry_async = inspect.iscoroutinefunction(
        retry_failed_assistant_message
    )

    print_result(
        "RAG generator is async",
        rag_async,
    )

    print_result(
        "Chat turn service is async",
        chat_async,
    )

    print_result(
        "Retry service is async",
        retry_async,
    )

    return (
        rag_async
        and chat_async
        and retry_async
    )


def test_routes():
    openapi_schema = app.openapi()

    route_paths = set(
        openapi_schema.get(
            "paths",
            {}
        ).keys()
    )

    required_routes = {
        "/health",
        "/api/v1/chats",
        "/api/v1/chats/{session_id}",
        "/api/v1/chats/{session_id}/messages",
        (
            "/api/v1/chats/{session_id}"
            "/messages/{message_id}/retry"
        ),
    }

    missing = (
        required_routes
        - route_paths
    )

    if missing:
        print_result(
            "Required API routes",
            False,
            "Missing: "
            + ", ".join(
                sorted(missing)
            ),
        )

        return False

    print_result(
        "Required API routes",
        True,
    )

    return True


def test_conversation_safety():
    messages = [
        {
            "role": "user",
            "content": (
                "How can I file a consumer complaint?"
            ),
        },
        {
            "role": "assistant",
            "content": (
                "INVENTED ASSISTANT LEGAL CLAIM"
            ),
        },
        {
            "role": "user",
            "content": "Where can I file it?",
        },
    ]

    query = build_conversation_query(
        current_question=(
            "What happens after admission?"
        ),
        messages=messages,
    )

    assistant_leaked = (
        "INVENTED ASSISTANT LEGAL CLAIM"
        in query
    )

    user_history_present = (
        "How can I file a consumer complaint?"
        in query
    )

    passed = (
        not assistant_leaked
        and user_history_present
    )

    print_result(
        "Conversation retrieval safety",
        passed,
        (
            "assistant messages excluded"
            if passed
            else "assistant content leaked into retrieval"
        ),
    )

    return passed


def test_supported_retrieval():
    results = search_legal_chunks(
        query=(
            "How can a consumer file "
            "a complaint against a seller?"
        ),
        top_k=5,
        category="consumer_rights",
    )

    if not results:
        print_result(
            "Supported retrieval",
            False,
            "No results",
        )
        return False

    confidence = (
        evaluate_retrieval_confidence(
            results
        )
    )

    passed = confidence[
        "accepted"
    ]

    print_result(
        "Supported retrieval",
        passed,
        (
            f"top_score="
            f"{confidence['top_score']:.4f}"
        ),
    )

    return passed


def test_unsupported_retrieval():
    results = search_legal_chunks(
        query=(
            "How do I register a patent "
            "for a new invention?"
        ),
        top_k=5,
        category=None,
    )

    if not results:
        print_result(
            "Unsupported rejection",
            True,
            "No retrieval results",
        )
        return True

    confidence = (
        evaluate_retrieval_confidence(
            results
        )
    )

    passed = not confidence[
        "accepted"
    ]

    print_result(
        "Unsupported rejection",
        passed,
        (
            f"top_score="
            f"{confidence['top_score']:.4f}, "
            f"accepted="
            f"{confidence['accepted']}"
        ),
    )

    return passed


async def test_rag_fallback():
    result = await generate_legal_answer(
        question=(
            "How do I register a patent "
            "for a new invention?"
        ),
        category=None,
        top_k=5,
    )

    sources = result.get(
        "sources",
        []
    )

    passed = (
        sources == []
        and "authoritative material"
        in result["answer"].lower()
    )

    print_result(
        "Unsupported RAG fallback",
        passed,
        f"sources={len(sources)}",
    )

    return passed


async def main():
    print()
    print("=" * 70)
    print("AI LEGAL BACKEND SMOKE TEST")
    print("=" * 70)
    print()

    results = []

    results.append(
        test_vector_store()
    )

    results.append(
        test_async_functions()
    )

    results.append(
        test_routes()
    )

    results.append(
        test_conversation_safety()
    )

    results.append(
        test_supported_retrieval()
    )

    results.append(
        test_unsupported_retrieval()
    )

    results.append(
        await test_rag_fallback()
    )

    print()
    print("=" * 70)

    passed_count = sum(
        1
        for result in results
        if result
    )

    total_count = len(
        results
    )

    print(
        f"Passed: {passed_count}/{total_count}"
    )

    if passed_count == total_count:
        print(
            "BACKEND SMOKE TEST: PASSED"
        )
    else:
        print(
            "BACKEND SMOKE TEST: FAILED"
        )

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(
        main()
    )