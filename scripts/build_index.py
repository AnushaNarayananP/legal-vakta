"""Build the Legal Vakta FAISS index from data/pdfs/**/*.pdf."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import Settings
from src.ingestion.pdf_loader import DocumentProcessor, find_pdf_files
from src.retrieval.vectorstore import create_vectorstore


def main():
    """Load PDFs, chunk text, create embeddings, and persist FAISS."""
    pdf_files = find_pdf_files(Settings.pdf_dir)
    print(f"Found {len(pdf_files)} PDFs under {Settings.pdf_dir}")

    processor = DocumentProcessor(
        chunk_size=Settings.chunk_size,
        chunk_overlap=Settings.chunk_overlap,
    )
    chunks = processor.process(Settings.pdf_dir)
    print(f"Created {len(chunks)} text chunks")

    create_vectorstore(chunks, Settings.vectorstore_dir)
    print(f"Saved FAISS index to {Settings.vectorstore_dir}")


if __name__ == "__main__":
    main()
