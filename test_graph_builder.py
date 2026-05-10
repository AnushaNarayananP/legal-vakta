from dataclasses import dataclass

from src.agent.graph_builder import (
    FALLBACK_RESPONSE,
    STUDENT_FALLBACK_RESPONSE,
    GraphBuilder,
)


@dataclass
class Document:
    page_content: str
    metadata: dict


@dataclass
class AIMessage:
    content: str


class FakeRetriever:
    def __init__(self, docs):
        self.docs = docs

    def invoke(self, _question):
        return self.docs


class FakeLLM:
    def __init__(self):
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return AIMessage(content="structured answer")


def test_graph_builder_returns_fallback_when_no_documents_are_retrieved():
    llm = FakeLLM()
    graph = GraphBuilder(retriever=FakeRetriever([]), llm=llm)

    result = graph.run("What is the law on benefit of doubt?")

    assert result["answer"] == FALLBACK_RESPONSE
    assert llm.messages is None


def test_graph_builder_prompt_requires_structured_legal_sections():
    doc = Document(
        page_content="The court discussed evidence and benefit of doubt.",
        metadata={"file_name": "case.pdf", "case_year": 2020, "page": 3},
    )
    llm = FakeLLM()
    graph = GraphBuilder(retriever=FakeRetriever([doc]), llm=llm)

    result = graph.run("What did the court say?")
    prompt_text = "\n".join(message.content for message in llm.messages)

    assert result["answer"] == "structured answer"
    assert "Key Insight" in prompt_text
    assert "Legal Issue" in prompt_text
    assert "Legal Reasoning" in prompt_text
    assert "Final Takeaway" in prompt_text
    assert "Source Evidence" in prompt_text
    assert "You are SpaceL AI, an AI legal research product" in prompt_text
    assert "Use ONLY the retrieved context." in prompt_text
    assert "Do not invent case names." in prompt_text
    assert "Do not invent citations." in prompt_text
    assert "The retrieved judgments provide limited direct discussion" in prompt_text
    assert f'"{FALLBACK_RESPONSE}"' in prompt_text


def test_graph_builder_student_mode_uses_student_prompt():
    doc = Document(
        page_content="The court explained the issue in simple terms.",
        metadata={"file_name": "case.pdf", "case_year": 2021, "page": 5},
    )
    llm = FakeLLM()
    graph = GraphBuilder(retriever=FakeRetriever([doc]), llm=llm)

    result = graph.run("Explain this case", mode="Student")
    prompt_text = "\n".join(message.content for message in llm.messages)

    assert result["answer"] == "structured answer"
    assert "designed to explain court judgments to law students" in prompt_text
    assert "Simple Explanation" in prompt_text
    assert "Legal Concept" in prompt_text
    assert "Simplified Source Evidence" in prompt_text
    assert STUDENT_FALLBACK_RESPONSE in prompt_text


def test_graph_builder_student_mode_returns_student_fallback_when_no_documents():
    llm = FakeLLM()
    graph = GraphBuilder(retriever=FakeRetriever([]), llm=llm)

    result = graph.run("Explain this case", mode="Student")

    assert result["answer"] == STUDENT_FALLBACK_RESPONSE
    assert llm.messages is None


def test_graph_builder_uses_langchain_compatible_message_shape():
    graph = GraphBuilder(retriever=FakeRetriever([]), llm=FakeLLM())
    messages = graph._build_messages("question", [])

    for message in messages:
        assert hasattr(message, "content")
        assert hasattr(message, "type")
        assert message.type in {"system", "human"}
