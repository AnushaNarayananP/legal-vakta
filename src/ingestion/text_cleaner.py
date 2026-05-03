"""Text cleaning utilities for Supreme Court judgment PDFs."""

import re
import unicodedata
from typing import Iterable, List

from langchain_core.documents import Document


_SPACE_RE = re.compile(r"[ \t]+")
_LINE_RE = re.compile(r"\n{3,}")
_BOILERPLATE_PATTERNS = [
    re.compile(r"^\s*downloaded from .*?$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE | re.MULTILINE),
]


def clean_text(text: str) -> str:
    """Normalize PDF text while preserving legal paragraph structure."""
    if not text:
        return ""

    cleaned = unicodedata.normalize("NFKC", text)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    for pattern in _BOILERPLATE_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    cleaned = _SPACE_RE.sub(" ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = _LINE_RE.sub("\n\n", cleaned)
    return cleaned.strip()


def clean_documents(documents: Iterable[Document]) -> List[Document]:
    """Clean LangChain documents and drop empty pages."""
    cleaned_docs: List[Document] = []

    for doc in documents:
        cleaned_text = clean_text(doc.page_content)
        if not cleaned_text:
            continue

        cleaned_docs.append(
            Document(page_content=cleaned_text, metadata=dict(doc.metadata))
        )

    return cleaned_docs
