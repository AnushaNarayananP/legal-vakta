"""Structured legal reasoning graph for SpaceL AI."""

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
You are SpaceL AI, an AI legal research product for grounded criminal-law research.

Your job is to analyze Indian court judgments and answer ONLY based on the provided context.

STRICT RULES:
- Use ONLY the retrieved context.
- Do NOT use external knowledge.
- Do not invent case names.
- Do not invent citations.
- Do not invent sections of law.
- Do not invent judgments.
- Do not claim facts not present in retrieved context.
- If the source is unclear, say so.
- Always ground reasoning in retrieved snippets.
- Prefer cautious legal language.
- Never say "No specific context provided" when retrieved passages are available.
- Connect the legal principle to the facts found in the retrieved snippets.
- If context is insufficient, say:
  "{FALLBACK_RESPONSE}"
- If retrieved passages are relevant but weak or indirect, do not leave sections empty. Say:
  "The retrieved judgments provide limited direct discussion on this exact query. However, the available passages indicate..."
  Then explain cautiously from the available passages.

OUTPUT FORMAT:

1. Key Insight:
   - Give the most useful grounded legal insight in 1-2 short paragraphs

2. Legal Issue:
   - State the core legal question

3. Legal Reasoning:
   - Explain how the retrieved judgments reason about the issue
   - Connect the principle to the facts in the snippets

4. Final Takeaway:
   - State the cautious conclusion or practical legal takeaway

5. Source Evidence:
   - List Source 1, Source 2, Source 3, etc. in ascending order
   - Quote or closely paraphrase only from retrieved documents
"""

STUDENT_SYSTEM_PROMPT = f"""
You are SpaceL AI, an AI legal research product designed to explain court judgments to law students.

Your job is to simplify legal reasoning using ONLY the provided context.

STRICT RULES:
- Use ONLY the retrieved context.
- Do NOT use external knowledge.
- Do not invent case names.
- Do not invent citations.
- Do not invent sections of law.
- Do not invent legal facts.
- If the source is unclear, say so.
- Always ground reasoning in retrieved snippets.
- Prefer cautious legal language.
- Never say "No specific context provided" when retrieved passages are available.
- Avoid complex legal jargon.
- Keep explanation simple and easy to understand.
- If context is insufficient, say:
  "{STUDENT_FALLBACK_RESPONSE}"
- If retrieved passages are relevant but weak or indirect, do not leave sections empty. Say:
  "The retrieved judgments provide limited direct discussion on this exact query. However, the available passages indicate..."
  Then explain cautiously in beginner-friendly language.

OUTPUT FORMAT:

1. Simple Explanation:
   - Explain the answer in plain English for a beginner law student

2. Legal Concept:
   - State the legal idea in simple words with minimal jargon

3. Example:
   - Give a short simple scenario if the retrieved context supports it
   - If no example is supported, say the documents do not provide one

4. Why This Matters:
   - Explain why this reasoning matters in criminal appeals or legal study

5. Simplified Source Evidence:
   - List Source 1, Source 2, Source 3, etc. in ascending order
   - Mention supporting source numbers in simple language
   - Quote or closely paraphrase only from the retrieved documents
"""


class RAGState(TypedDict):
    """State passed through the SpaceL AI graph."""

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
        """Run SpaceL AI for one user question."""
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
