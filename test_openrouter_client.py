from dataclasses import dataclass

from src.llm.openrouter_client import (
    FALLBACK_MODEL_1,
    FALLBACK_MODEL_2,
    PRIMARY_MODEL,
    OpenRouterChatLLM,
    call_openrouter_llm,
)


@dataclass
class Message:
    type: str
    content: str


class FakeChoice:
    def __init__(self, content):
        self.message = type("Message", (), {"content": content})


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self, fail_models=None):
        self.fail_models = set(fail_models or [])
        self.called_models = []

    def create(self, model, messages, temperature, max_tokens):
        self.called_models.append(model)
        if model in self.fail_models:
            raise RuntimeError(f"{model} failed")
        return FakeResponse(f"answer from {model}")


class FakeClient:
    def __init__(self, fail_models=None):
        self.chat = type("Chat", (), {"completions": FakeCompletions(fail_models)})()


def test_call_openrouter_llm_uses_primary_model_first():
    client = FakeClient()

    answer = call_openrouter_llm("system", "user", client=client)

    assert answer.startswith(f"answer from {PRIMARY_MODEL}")
    assert client.chat.completions.called_models == [PRIMARY_MODEL]


def test_call_openrouter_llm_tries_fallback_models_in_order():
    client = FakeClient(
        fail_models={
            PRIMARY_MODEL,
            FALLBACK_MODEL_1,
        }
    )

    answer = call_openrouter_llm("system", "user", client=client)

    assert answer.startswith(f"answer from {FALLBACK_MODEL_2}")
    assert client.chat.completions.called_models == [
        PRIMARY_MODEL,
        FALLBACK_MODEL_1,
        FALLBACK_MODEL_2,
    ]


def test_openrouter_chat_llm_accepts_langchain_style_messages():
    client = FakeClient()
    llm = OpenRouterChatLLM(client=client)

    response = llm.invoke(
        [
            Message(type="system", content="system prompt"),
            Message(type="human", content="user prompt"),
        ]
    )

    assert response.content.startswith("answer from")
