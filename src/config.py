"""Central configuration for SpaceL AI."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings:
    """Project paths and runtime defaults."""

    app_name = "SpaceL AI - Criminal Case Research Assistant"

    data_dir = PROJECT_ROOT / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    pdf_dir = data_dir / "pdfs"
    vectorstore_dir = PROJECT_ROOT / "vectorstore"

    raw_csv_path = raw_dir / "judgments.csv"
    selected_csv_path = processed_dir / "selected_judgments.csv"

    chunk_size = 900
    chunk_overlap = 150
    embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    retriever_k = 5
    llm_model = "qwen/qwen3-next-80b-a3b-instruct:free"
    demo_video_url = os.getenv("SPACEL_DEMO_VIDEO_URL", "https://youtu.be/a5OXVLpDyH4")
    fallback_query_count = int(os.getenv("SPACEL_FALLBACK_QUERY_COUNT", "120"))
    fallback_helpful_percent = int(os.getenv("SPACEL_FALLBACK_HELPFUL_PERCENT", "78"))


def get_llm(model: Optional[str] = None, temperature: Optional[float] = None):
    """Create the OpenRouter chat model used by the agent graph."""
    from src.llm.openrouter_client import OpenRouterChatLLM

    return OpenRouterChatLLM(model=model or Settings.llm_model, temperature=temperature)
