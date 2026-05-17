from src.retrieval import vectorstore


def test_create_embeddings_retries_processor_error_with_local_files_only(monkeypatch):
    calls = []

    def fake_huggingface_embeddings(**kwargs):
        calls.append(kwargs)
        if not kwargs.get("model_kwargs", {}).get("local_files_only"):
            raise ValueError("Unrecognized processing class in sentence-transformers/all-MiniLM-L6-v2.")
        return "embeddings"

    vectorstore.create_embeddings.cache_clear()
    monkeypatch.setattr(vectorstore, "HuggingFaceEmbeddings", fake_huggingface_embeddings)

    assert vectorstore.create_embeddings("sentence-transformers/all-MiniLM-L6-v2") == "embeddings"
    assert calls == [
        {"model_name": "sentence-transformers/all-MiniLM-L6-v2"},
        {
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "model_kwargs": {"local_files_only": True},
        },
    ]
