"""FAISS vector store creation and loading."""

from pathlib import Path
from typing import Iterable, Union

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from src.config import Settings


def create_embeddings(model_name: str = Settings.embedding_model):
    """Create local sentence-transformer embeddings."""
    return HuggingFaceEmbeddings(model_name=model_name)


def create_vectorstore(
    documents: Iterable[Document],
    persist_dir: Union[str, Path] = Settings.vectorstore_dir,
    embedding_model: str = Settings.embedding_model,
):
    """Create a FAISS index from documents and save index.faiss/index.pkl."""
    docs = list(documents)
    if not docs:
        raise ValueError("Cannot create vectorstore: no documents were provided.")

    persist_path = Path(persist_dir)
    persist_path.mkdir(parents=True, exist_ok=True)

    embeddings = create_embeddings(embedding_model)
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local(str(persist_path))
    return vectorstore


def load_vectorstore(
    persist_dir: Union[str, Path] = Settings.vectorstore_dir,
    embedding_model: str = Settings.embedding_model,
):
    """Load a persisted FAISS vector store."""
    persist_path = Path(persist_dir)
    index_path = persist_path / "index.faiss"
    metadata_path = persist_path / "index.pkl"

    if not index_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(
            f"Vectorstore not found in {persist_path}. Run scripts/build_index.py first."
        )

    embeddings = create_embeddings(embedding_model)
    return FAISS.load_local(
        str(persist_path),
        embeddings,
        allow_dangerous_deserialization=True,
    )


def get_retriever(vectorstore, k: int = Settings.retriever_k):
    """Return a top-k retriever from a FAISS vector store."""
    return vectorstore.as_retriever(search_kwargs={"k": k})


class VectorStore:
    """Small OO wrapper compatible with the earlier project API."""

    def __init__(self, persist_dir: Union[str, Path] = Settings.vectorstore_dir):
        self.persist_dir = Path(persist_dir)
        self.vectorstore = None

    def create_vectorstore(self, documents: Iterable[Document]):
        self.vectorstore = create_vectorstore(documents, self.persist_dir)
        return self.vectorstore

    def load_vectorstore(self):
        self.vectorstore = load_vectorstore(self.persist_dir)
        return self.vectorstore

    def get_retriever(self, k: int = Settings.retriever_k):
        if self.vectorstore is None:
            self.load_vectorstore()
        return get_retriever(self.vectorstore, k=k)
