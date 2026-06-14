"""OpenRouter chat client for SpaceL AI."""

import os
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional

from dotenv import load_dotenv

load_dotenv()


OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
PRIMARY_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    os.getenv(
        "PRIMARY_MODEL",
        "anthropic/claude-haiku-4.5",
    ),
)
FALLBACK_MODEL_1 = os.getenv(
    "OPENROUTER_FALLBACK_MODEL_1",
    os.getenv(
        "FALLBACK_MODEL_1",
        os.getenv("BACKUP_MODEL_1", "openai/gpt-4o-mini"),
    ),
)
OPENROUTER_TEMPERATURE = float(os.getenv("OPENROUTER_TEMPERATURE", "0.2"))
OPENROUTER_MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS", "2048"))
MODEL_FALLBACKS = [PRIMARY_MODEL, FALLBACK_MODEL_1]


class OpenRouterLLMError(RuntimeError):
    """Raised when every configured OpenRouter model fails."""


@dataclass
class LLMResponse:
    """Minimal response object compatible with GraphBuilder expectations."""

    content: str


def get_openrouter_client():
    """Create an OpenAI-compatible OpenRouter client."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip().strip('"')
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured.")

    from openai import OpenAI

    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)


def _message_to_dict(message):
    """Convert LangChain-style messages into OpenAI chat message dicts."""
    role = getattr(message, "type", None) or getattr(message, "role", None)
    content = getattr(message, "content", "")

    if role == "human":
        role = "user"
    elif role == "ai":
        role = "assistant"
    elif role not in {"system", "user", "assistant"}:
        role = "user"

    return {"role": role, "content": content}


def messages_to_prompt_parts(messages: Iterable) -> tuple[str, str]:
    """Split message list into system and user prompt strings."""
    system_parts: List[str] = []
    user_parts: List[str] = []

    for message in messages:
        message_dict = _message_to_dict(message)
        if message_dict["role"] == "system":
            system_parts.append(message_dict["content"])
        else:
            user_parts.append(message_dict["content"])

    return "\n\n".join(system_parts), "\n\n".join(user_parts)


def call_openrouter_llm(
    system_prompt: str,
    user_prompt: str,
    client=None,
    models: Optional[List[str]] = None,
    temperature: Optional[float] = None,
    token_callback: Optional[Callable[[str], None]] = None,
) -> str:
    """Call OpenRouter with primary model, then fallbacks on failure."""
    openrouter_client = client or get_openrouter_client()
    model_order = models or MODEL_FALLBACKS
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    errors = []

    for model in model_order:
        try:
            request = {
                "model": model,
                "messages": messages,
                "temperature": OPENROUTER_TEMPERATURE if temperature is None else temperature,
                "max_tokens": OPENROUTER_MAX_TOKENS,
            }
            if token_callback is None:
                response = openrouter_client.chat.completions.create(**request)
                return response.choices[0].message.content.strip()

            stream = openrouter_client.chat.completions.create(**request, stream=True)
            chunks = []
            for chunk in stream:
                choices = getattr(chunk, "choices", []) or []
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                token = getattr(delta, "content", None) if delta is not None else None
                if not token:
                    continue
                chunks.append(token)
                token_callback(token)
            return "".join(chunks).strip()
        except Exception as exc:
            errors.append(f"{model}: {exc}")

    raise OpenRouterLLMError("All OpenRouter models failed. " + " | ".join(errors))


class OpenRouterChatLLM:
    """Small LangChain-compatible chat wrapper used by GraphBuilder."""

    def __init__(self, client=None, model: Optional[str] = None, temperature: Optional[float] = None):
        self.client = client
        self.models = [model] + [item for item in MODEL_FALLBACKS if item != model] if model else None
        self.temperature = temperature
        self.token_callback = None

    def set_stream_callback(self, token_callback: Optional[Callable[[str], None]]):
        """Attach a temporary token callback for Streamlit response streaming."""
        self.token_callback = token_callback

    def invoke(self, messages):
        """Invoke OpenRouter using LangChain-style chat messages."""
        system_prompt, user_prompt = messages_to_prompt_parts(messages)
        answer = call_openrouter_llm(
            system_prompt,
            user_prompt,
            client=self.client,
            models=self.models,
            temperature=self.temperature,
            token_callback=self.token_callback,
        )
        return LLMResponse(content=answer)
