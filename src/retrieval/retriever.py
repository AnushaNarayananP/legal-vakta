"""Explainable retrieval helpers for Legal Vakta."""

from pathlib import Path
from typing import Dict, List

from langchain_core.documents import Document


def format_source_metadata(doc: Document) -> Dict[str, object]:
    """Extract source fields shown in the CLI and Streamlit UI."""
    metadata = dict(doc.metadata)
    source = metadata.get("source", "")
    file_name = metadata.get("file_name") or Path(str(source)).name

    return {
        "file_name": file_name,
        "case_year": metadata.get("case_year"),
        "page": metadata.get("page"),
        "source": source,
    }


class LegalRetriever:
    """Top-k retrieval with source metadata."""

    def __init__(self, retriever):
        self.retriever = retriever

    def retrieve(self, query: str) -> List[Dict[str, object]]:
        """Return relevant chunks plus filename/year metadata."""
        docs = self.retriever.invoke(query)
        results = []

        for doc in docs:
            results.append(
                {
                    "content": doc.page_content,
                    "metadata": format_source_metadata(doc),
                    "document": doc,
                }
            )

        return results
