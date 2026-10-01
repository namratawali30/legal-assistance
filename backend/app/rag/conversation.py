from typing import Any


MAX_HISTORY_MESSAGES = 6
MAX_HISTORY_CHARS = 3000


def get_recent_user_messages(
    messages: list[dict[str, Any]],
    limit: int = MAX_HISTORY_MESSAGES,
) -> list[str]:
    user_messages = []

    for message in reversed(messages):
        if message.get("role") != "user":
            continue

        content = str(
            message.get(
                "content",
                ""
            )
        ).strip()

        if not content:
            continue

        user_messages.append(
            content
        )

        if len(user_messages) >= limit:
            break

    user_messages.reverse()

    return user_messages


def build_conversation_query(
    current_question: str,
    messages: list[dict[str, Any]],
    case_context: dict[str, Any] | None = None,
) -> str:
    current_question = current_question.strip()

    if not current_question:
        raise ValueError(
            "Current question cannot be empty"
        )

    history = get_recent_user_messages(
        messages
    )

    # Avoid duplicating current question if it was
    # already stored before this function is called.
    if (
        history
        and history[-1].strip().lower()
        == current_question.lower()
    ):
        history = history[:-1]

    history_text = "\n".join(
        f"- {message}"
        for message in history
    )

    if len(history_text) > MAX_HISTORY_CHARS:
        history_text = history_text[
            -MAX_HISTORY_CHARS:
        ]

    context_summary_lines = []
    if case_context:
        for k, v in case_context.items():
            if v and isinstance(v, str):
                context_summary_lines.append(f"{k.replace('_', ' ').title()}: {v}")

    context_str = "\n".join(context_summary_lines) if context_summary_lines else ""

    parts = []
    if context_str:
        parts.append(f"Established Case Facts:\n{context_str}")
    if history_text:
        parts.append(f"Previous user questions in this legal conversation:\n{history_text}")
    parts.append(f"Current user question:\n{current_question}")

    return "\n\n".join(parts)