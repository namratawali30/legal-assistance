from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from app.config import settings


_client: AsyncOpenAI | None = None


class LLMServiceError(Exception):
    """Base exception for LLM provider failures."""


class LLMRateLimitError(LLMServiceError):
    """Raised when the provider rate limit is exceeded."""


class LLMTimeoutError(LLMServiceError):
    """Raised when the provider request times out."""


class LLMConnectionError(LLMServiceError):
    """Raised when the provider cannot be reached."""


def get_llm_client() -> AsyncOpenAI:
    global _client

    if _client is not None:
        return _client

    if not settings.llm_api_key:
        raise LLMServiceError(
            "LLM_API_KEY is not configured"
        )

    if settings.llm_provider == "openrouter":
        _client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=60.0,
        )
    else:
        _client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            timeout=60.0,
        )

    return _client


async def generate_text(
    instructions: str,
    input_text: str,
) -> str:
    client = get_llm_client()

    try:
        if settings.llm_provider == "openrouter":
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": instructions,
                    },
                    {
                        "role": "user",
                        "content": input_text,
                    },
                ],
                temperature=0.1,
            )

            answer = (
                response
                .choices[0]
                .message
                .content
            )

        else:
            response = await client.responses.create(
                model=settings.llm_model,
                instructions=instructions,
                input=input_text,
            )

            answer = response.output_text

    except RateLimitError as exc:
        raise LLMRateLimitError(
            "LLM provider rate limit exceeded"
        ) from exc

    except APITimeoutError as exc:
        raise LLMTimeoutError(
            "LLM provider request timed out"
        ) from exc

    except APIConnectionError as exc:
        raise LLMConnectionError(
            "Could not connect to LLM provider"
        ) from exc

    except LLMServiceError:
        raise

    except Exception as exc:
        raise LLMServiceError(
            "LLM generation failed"
        ) from exc

    if not answer:
        raise LLMServiceError(
            "LLM returned an empty response"
        )

    return answer.strip()