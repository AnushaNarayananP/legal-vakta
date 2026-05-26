from dataclasses import dataclass

from src.llm.openrouter_client import (
    FALLBACK_MODEL_1,
    MODEL_FALLBACKS,
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


class FakeDelta:
    def __init__(self, content):
        self.content = content


class FakeChunkChoice:
    def __init__(self, content):
        self.delta = FakeDelta(content)


class FakeChunk:
    def __init__(self, content):
        self.choices = [FakeChunkChoice(content)]


class FakeCompletions:
    def __init__(self, fail_models=None):
        self.fail_models = set(fail_models or [])
        self.called_models = []
        self.stream_values = []

    def create(self, model, messages, temperature, max_tokens, stream=False):
        self.called_models.append(model)
        self.stream_values.append(stream)
        if model in self.fail_models:
            raise RuntimeError(f"{model} failed")
        if stream:
            return iter([FakeChunk("streamed "), FakeChunk("answer")])
        return FakeResponse(f"answer from {model}")


class FakeClient:
    def __init__(self, fail_models=None):
        self.chat = type("Chat", (), {"completions": FakeCompletions(fail_models)})()


def test_call_openrouter_llm_uses_primary_model_first():
    client = FakeClient()

    answer = call_openrouter_llm("system", "user", client=client)

    assert answer.startswith(f"answer from {PRIMARY_MODEL}")
    assert client.chat.completions.called_models == [PRIMARY_MODEL]


def test_openrouter_defaults_to_claude_haiku_with_gpt_4o_mini_fallback():
    assert PRIMARY_MODEL == "anthropic/claude-haiku-4.5"
    assert FALLBACK_MODEL_1 == "openai/gpt-4o-mini"
    assert MODEL_FALLBACKS[:2] == [
        "anthropic/claude-haiku-4.5",
        "openai/gpt-4o-mini",
    ]


def test_call_openrouter_llm_tries_fallback_models_in_order():
    client = FakeClient(
        fail_models={
            PRIMARY_MODEL,
        }
    )

    answer = call_openrouter_llm("system", "user", client=client)

    assert answer.startswith(f"answer from {FALLBACK_MODEL_1}")
    assert client.chat.completions.called_models == [
        PRIMARY_MODEL,
        FALLBACK_MODEL_1,
    ]


def test_call_openrouter_llm_streams_tokens_to_callback():
    client = FakeClient()
    tokens = []

    answer = call_openrouter_llm("system", "user", client=client, token_callback=tokens.append)

    assert answer == "streamed answer"
    assert tokens == ["streamed ", "answer"]
    assert client.chat.completions.stream_values == [True]


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


def test_openrouter_chat_llm_uses_stream_callback_when_set():
    client = FakeClient()
    tokens = []
    llm = OpenRouterChatLLM(client=client)
    llm.set_stream_callback(tokens.append)

    response = llm.invoke(
        [
            Message(type="system", content="system prompt"),
            Message(type="human", content="user prompt"),
        ]
    )

    assert response.content == "streamed answer"
    assert tokens == ["streamed ", "answer"]
