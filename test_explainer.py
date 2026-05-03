from dataclasses import dataclass

from src.agent.explainer import (
    EXPLAIN_FALLBACK_RESPONSE,
    EXPLAIN_PROMPT,
    build_explain_messages,
    explain_answer_for_law_students,
)


@dataclass
class Document:
    page_content: str
    metadata: dict


@dataclass
class AIMessage:
    content: str


class FakeLLM:
    def __init__(self):
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return AIMessage(content="simple explanation")


def test_explain_prompt_uses_only_context_and_answer():
    assert "Use ONLY the provided context and answer" in EXPLAIN_PROMPT
    assert "Do NOT add external legal knowledge" in EXPLAIN_PROMPT
    assert "Do NOT invent case laws" in EXPLAIN_PROMPT
    assert EXPLAIN_FALLBACK_RESPONSE in EXPLAIN_PROMPT


def test_build_explain_messages_includes_context_and_structured_answer():
    doc = Document(
        page_content="The court gave benefit of doubt because evidence was weak.",
        metadata={"file_name": "case.pdf", "case_year": 2020, "page": 4},
    )

    messages = build_explain_messages([doc], "1. Legal Issue:\n- Benefit of doubt.")
    prompt_text = "\n".join(message.content for message in messages)

    assert messages[0].type == "system"
    assert messages[1].type == "human"
    assert "Source 1" in prompt_text
    assert "case.pdf" in prompt_text
    assert "Benefit of doubt" in prompt_text


def test_explain_answer_returns_fallback_when_context_or_answer_is_missing():
    llm = FakeLLM()

    assert explain_answer_for_law_students(llm, [], "answer") == EXPLAIN_FALLBACK_RESPONSE
    assert explain_answer_for_law_students(llm, [Document("text", {})], "") == EXPLAIN_FALLBACK_RESPONSE
    assert llm.messages is None


def test_explain_answer_invokes_llm_with_langchain_messages():
    llm = FakeLLM()
    doc = Document(page_content="Evidence was doubtful.", metadata={})

    explanation = explain_answer_for_law_students(llm, [doc], "Structured answer")

    assert explanation == "simple explanation"
    assert [message.type for message in llm.messages] == ["system", "human"]
