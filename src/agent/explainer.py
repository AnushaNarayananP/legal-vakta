"""Law-student explanation helper for Legal Vakta answers."""

from typing import List

from langchain_core.messages import HumanMessage, SystemMessage


EXPLAIN_FALLBACK_RESPONSE = "Cannot simplify due to insufficient legal context."

EXPLAIN_PROMPT = f"""
You are Legal Vakta, an AI legal research assistant.

You will be given:
1. Retrieved legal context
2. A structured legal answer

Your job is to explain the answer in a way a LAW STUDENT can easily understand.

STRICT RULES:
- Use ONLY the provided context and answer
- Do NOT add external legal knowledge
- Keep explanation simple and clear
- Avoid complex legal jargon
- Do NOT invent case laws

OUTPUT FORMAT:

Simplified Explanation (For Law Students):

- Explain the concept in plain English
- Break down legal reasoning step-by-step
- Use simple examples if needed
- Highlight key takeaway

Key Legal Principle:

- One-line summary of the rule

If context is insufficient, say:
"{EXPLAIN_FALLBACK_RESPONSE}"
"""


def format_explain_context(documents: List[object]) -> str:
    """Convert retrieved documents into source-labeled context."""
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


def build_explain_messages(documents: List[object], structured_answer: str):
    """Build messages for the law-student explanation step."""
    context = format_explain_context(documents)
    user_prompt = (
        f"Retrieved legal context:\n{context}\n\n"
        f"Structured legal answer:\n{structured_answer}\n\n"
        "Explain the answer using the required format."
    )

    return [
        SystemMessage(content=EXPLAIN_PROMPT),
        HumanMessage(content=user_prompt),
    ]


def explain_answer_for_law_students(llm, documents: List[object], structured_answer: str) -> str:
    """Generate a simple law-student explanation from retrieved context and answer."""
    if not documents or not structured_answer.strip():
        return EXPLAIN_FALLBACK_RESPONSE

    messages = build_explain_messages(documents, structured_answer)
    response = llm.invoke(messages)
    explanation = getattr(response, "content", str(response)).strip()
    return explanation or EXPLAIN_FALLBACK_RESPONSE
