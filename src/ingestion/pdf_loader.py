"""Recursive PDF loading for SpaceL AI."""

from pathlib import Path
from typing import Iterable, List, Union

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import Settings
from src.ingestion.text_cleaner import clean_documents


def find_pdf_files(pdf_dir: Union[str, Path] = Settings.pdf_dir) -> List[Path]:
    """Return all PDFs under data/pdfs recursively."""
    root = Path(pdf_dir)
    if not root.exists():
        raise FileNotFoundError(f"PDF directory not found: {root}")

    return sorted(root.glob("**/*.pdf"))


def infer_case_year(pdf_path: Path, pdf_root: Union[str, Path] = Settings.pdf_dir):
    """Infer case year from a year folder in the PDF path when available."""
    root = Path(pdf_root)
    try:
        parts = pdf_path.relative_to(root).parts
    except ValueError:
        parts = pdf_path.parts

    for part in parts:
        if part.isdigit() and 1900 <= int(part) <= 2099:
            return int(part)
    return None


def load_pdf(pdf_path: Union[str, Path], pdf_root: Union[str, Path] = Settings.pdf_dir):
    """Load a single PDF and enrich page metadata."""
    path = Path(pdf_path)
    loader = PyPDFLoader(str(path))
    documents = loader.load()
    year = infer_case_year(path, pdf_root)

    for doc in documents:
        doc.metadata.update(
            {
                "source": str(path),
                "file_name": path.name,
                "case_year": year,
            }
        )

    return documents


def load_pdfs_from_folder(pdf_dir: Union[str, Path] = Settings.pdf_dir) -> List[Document]:
    """Load all PDFs recursively from data/pdfs."""
    pdf_paths = find_pdf_files(pdf_dir)
    documents: List[Document] = []

    for pdf_path in pdf_paths:
        try:
            documents.extend(load_pdf(pdf_path, pdf_dir))
        except Exception as exc:
            print(f"Skipping unreadable PDF: {pdf_path} ({exc})")

    return clean_documents(documents)


class DocumentProcessor:
    """Load, clean, and split judgment PDFs into retrieval chunks."""

    def __init__(
        self,
        chunk_size: int = Settings.chunk_size,
        chunk_overlap: int = Settings.chunk_overlap,
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def load_documents(self, pdf_dir: Union[str, Path] = Settings.pdf_dir) -> List[Document]:
        """Load all PDFs from a directory recursively."""
        return load_pdfs_from_folder(pdf_dir)

    def split_documents(self, documents: Iterable[Document]) -> List[Document]:
        """Split cleaned documents into chunks."""
        return self.splitter.split_documents(list(documents))

    def process(self, pdf_dir: Union[str, Path] = Settings.pdf_dir) -> List[Document]:
        """Full ingestion pipeline: load, clean, and chunk PDFs."""
        documents = self.load_documents(pdf_dir)
        return self.split_documents(documents)
