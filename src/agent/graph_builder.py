"""Structured legal reasoning graph for Legal Vakta."""

from typing import List, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # Keeps unit tests/imports usable before dependencies install.
    END = None
    StateGraph = None


FALLBACK_RESPONSE = "Relevant legal material not found in provided documents."
STUDENT_FALLBACK_RESPONSE = "Cannot explain due to insufficient legal context."
LEGAL_MODE = "Legal"
STUDENT_MODE = "Student"

LEGAL_RESEARCH_SYSTEM_PROMPT = f"""
You are Legal Vakta, an AI legal research assistant.

Your job is to analyze Indian court judgments and answer ONLY based on the provided context.

STRICT RULES:
- Use ONLY the retrieved context.
- Do NOT use external knowledge.
- Do NOT invent case names, sections, or judgments.
- If context is insufficient, say:
  "{FALLBACK_RESPONSE}"

OUTPUT FORMAT:

1. Legal Issue:
   - What is the core legal question?

2. Relevant Case Context:
   - Summarize key points from retrieved sources
   - Mention source numbers clearly

3. Legal Reasoning:
   - Explain how the court analyzed the issue

4. Possible Legal Direction:
   - What legal principle can be derived?

5. Source Evidence:
   - Quote exact lines from documents (with source numbers)
"""

STUDENT_SYSTEM_PROMPT = f"""
You are Legal Vakta, an AI legal assistant designed to explain court judgments to law students.

Your job is to simplify legal reasoning using ONLY the provided context.

STRICT RULES:
- Use ONLY the retrieved context.
- Do NOT use external knowledge.
- Do NOT invent case laws or legal facts.
- Avoid complex legal jargon.
- Keep explanation simple and easy to understand.
- If context is insufficient, say:
  "{STUDENT_FALLBACK_RESPONSE}"

OUTPUT FORMAT:

Simplified Explanation (For Law Students):
- Explain the concept in plain English
- Break down reasoning step-by-step
- Keep it clear and easy

Key Legal Principle:
- One-line summary of the rule

From Cases:
- Mention which sources support the explanation
"""


class RAGState(TypedDict):
    """State passed through the Legal Vakta graph."""

    question: str
    retrieved_docs: List[object]
    answer: str
    mode: str


class GraphBuilder:
    """Build and run a retrieval-then-structured-reasoning workflow."""

    def __init__(self, retriever, llm):
        self.retriever = retriever
        self.llm = llm
        self.graph = None

    def retrieve_docs(self, state: RAGState) -> RAGState:
        """Fetch relevant judgment chunks."""
        docs = self.retriever.invoke(state["question"])
        return {**state, "retrieved_docs": docs}

    def _format_context(self, documents: List[object]) -> str:
        """Convert retrieved chunks into source-labeled prompt context."""
        context_blocks = []

        for index, doc in enumerate(documents, start=1):
            metadata = getattr(doc, "metadata", {}) or {}
            file_name = metadata.get("file_name") or metadata.get("source", "unknown")
            year = metadata.get("case_year", "unknown")
            page = metadata.get("page", "unknown")
            page_content = getattr(doc, "page_content", "")

            context_blocks.append(
                f"Source {index}\n"
                f"- PDF filename: {file_name}\n"
                f"- Case year: {year}\n"
                f"- Page: {page}\n"
                f"- Excerpt:\n{page_content}"
            )

        return "\n\n".join(context_blocks)

    def _resolve_mode(self, mode: str) -> str:
        """Normalize unsupported modes to the default legal mode."""
        return STUDENT_MODE if str(mode).lower() == STUDENT_MODE.lower() else LEGAL_MODE

    def _get_system_prompt(self, mode: str) -> str:
        """Return the system prompt for the selected answer mode."""
        return STUDENT_SYSTEM_PROMPT if self._resolve_mode(mode) == STUDENT_MODE else LEGAL_RESEARCH_SYSTEM_PROMPT

    def _get_fallback_response(self, mode: str) -> str:
        """Return the deterministic fallback for the selected answer mode."""
        return STUDENT_FALLBACK_RESPONSE if self._resolve_mode(mode) == STUDENT_MODE else FALLBACK_RESPONSE

    def _build_messages(self, question: str, documents: List[object], mode: str = LEGAL_MODE):
        """Build grounded messages for the selected mode."""
        context = self._format_context(documents)
        user_prompt = (
            f"Research question:\n{question}\n\n"
            f"Retrieved document excerpts:\n{context}\n\n"
            "Generate the answer using the required structure."
        )

        return [
            SystemMessage(content=self._get_system_prompt(mode)),
            HumanMessage(content=user_prompt),
        ]

    def generate_answer(self, state: RAGState) -> RAGState:
        """Generate grounded structured output or deterministic fallback."""
        documents = state.get("retrieved_docs", [])
        mode = self._resolve_mode(state.get("mode", LEGAL_MODE))
        if not documents:
            return {**state, "answer": self._get_fallback_response(mode)}

        messages = self._build_messages(state["question"], documents, mode=mode)
        response = self.llm.invoke(messages)
        answer = getattr(response, "content", str(response)).strip()

        if not answer:
            answer = self._get_fallback_response(mode)

        return {**state, "answer": answer}

    def build(self):
        """Compile the LangGraph graph when langgraph is installed."""
        if StateGraph is None:
            self.graph = None
            return None

        builder = StateGraph(RAGState)
        builder.add_node("retrieve", self.retrieve_docs)
        builder.add_node("answer", self.generate_answer)
        builder.set_entry_point("retrieve")
        builder.add_edge("retrieve", "answer")
        builder.add_edge("answer", END)
        self.graph = builder.compile()
        return self.graph

    def run(self, question: str, mode: str = LEGAL_MODE) -> RAGState:
        """Run Legal Vakta for one user question."""
        initial_state = {
            "question": question,
            "retrieved_docs": [],
            "answer": "",
            "mode": self._resolve_mode(mode),
        }

        if StateGraph is None:
            state = self.retrieve_docs(initial_state)
            return self.generate_answer(state)

        if self.graph is None:
            self.build()

        return self.graph.invoke(initial_state)
