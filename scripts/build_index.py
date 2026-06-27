"""Build the Legal Vakta FAISS index from data/pdfs/**/*.pdf.

This script:
  1. Loads and chunks all PDFs
  2. Extracts timeline events per PDF via LLM (stored as metadata)
  3. Persists the enriched chunks into a FAISS index

Fault-tolerance features:
  - JSON checkpoint (``vectorstore/timeline_checkpoint.json``) saves after
    every successful PDF extraction so progress is never lost.
  - On restart, already-processed PDFs are skipped automatically (resume).
  - ``openai.RateLimitError`` triggers a clean exit after saving progress.
  - Other API errors are logged per-PDF but do not halt the pipeline.
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import Settings
from src.ingestion.pdf_loader import DocumentProcessor, find_pdf_files
from src.llm.timeline_extractor import extract_timeline_from_text
from src.retrieval.vectorstore import create_vectorstore

# Checkpoint lives next to the FAISS index so they stay in sync.
CHECKPOINT_PATH = Settings.vectorstore_dir / "timeline_checkpoint.json"


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def _load_checkpoint() -> dict:
    """Load the existing checkpoint or return an empty dict."""
    if CHECKPOINT_PATH.exists():
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  ⚠ Could not load checkpoint ({exc}), starting fresh")
    return {}


def _save_checkpoint(checkpoint: dict) -> None:
    """Atomically write the checkpoint to disk."""
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CHECKPOINT_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False)
    tmp.replace(CHECKPOINT_PATH)


# ---------------------------------------------------------------------------
# Rate-limit detection
# ---------------------------------------------------------------------------

def _is_rate_limit_error(exc: Exception) -> bool:
    """Return True if *exc* is an OpenAI / OpenRouter rate-limit (429) error."""
    # openai.RateLimitError (openai >= 1.x)
    try:
        import openai
        if isinstance(exc, openai.RateLimitError):
            return True
    except ImportError:
        pass

    # Fallback: check for 429 in string repr (covers wrapped HTTP errors)
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "quota" in msg


# ---------------------------------------------------------------------------
# Core enrichment logic
# ---------------------------------------------------------------------------

def _enrich_chunks_with_timelines(chunks):
    """Extract one timeline per PDF and attach it to every chunk from that PDF.

    Groups chunks by ``file_name``, concatenates page text per PDF (capped at
    3 000 chars to match the extractor's internal limit), makes one LLM call
    per PDF, then copies the result into ``chunk.metadata["pre_extracted_timeline"]``
    for every chunk belonging to that PDF.

    Progress is checkpointed to ``CHECKPOINT_PATH`` after every PDF so that
    a crash or quota-limit never loses already-extracted data.
    """
    # Group chunks by source PDF
    by_file = defaultdict(list)
    for chunk in chunks:
        fname = chunk.metadata.get("file_name", "unknown")
        by_file[fname].append(chunk)

    total_pdfs = len(by_file)

    # Load checkpoint — skip PDFs already processed
    checkpoint = _load_checkpoint()
    already_done = set(checkpoint.keys()) & set(by_file.keys())
    if already_done:
        print(
            f"Checkpoint found: {len(already_done)}/{total_pdfs} PDFs already "
            f"processed — resuming remaining {total_pdfs - len(already_done)}"
        )

    start = time.perf_counter()
    success_count = sum(1 for f in already_done if checkpoint.get(f))
    empty_count = sum(1 for f in already_done if not checkpoint.get(f))
    processed_this_run = 0
    rate_limited = False

    for idx, (fname, file_chunks) in enumerate(by_file.items(), start=1):
        # --- Apply cached checkpoint data (skip LLM call) ---
        if fname in checkpoint:
            timeline = checkpoint[fname]
            for c in file_chunks:
                c.metadata["pre_extracted_timeline"] = timeline
            continue

        # --- Build representative text from this PDF's chunks ---
        combined_text = ""
        for c in file_chunks:
            combined_text += c.page_content + "\n"
            if len(combined_text) >= 3000:
                break

        # --- LLM extraction with fault tolerance ---
        try:
            timeline = extract_timeline_from_text(combined_text[:3000])
        except Exception as exc:
            if _is_rate_limit_error(exc):
                print(f"\n  🛑 Rate limit hit at PDF {idx}/{total_pdfs} ({fname})")
                print(f"     Saving checkpoint with {len(checkpoint)} PDFs...")
                _save_checkpoint(checkpoint)
                rate_limited = True
                break
            else:
                print(f"  ⚠ Timeline extraction failed for {fname}: {exc}")
                timeline = []

        # Attach to every chunk from this PDF
        for c in file_chunks:
            c.metadata["pre_extracted_timeline"] = timeline

        # Persist immediately
        checkpoint[fname] = timeline
        _save_checkpoint(checkpoint)

        if timeline:
            success_count += 1
        else:
            empty_count += 1

        processed_this_run += 1
        if processed_this_run % 20 == 0 or idx == total_pdfs:
            elapsed = time.perf_counter() - start
            print(f"  [{idx}/{total_pdfs}] processed  ({elapsed:.1f}s elapsed)")

    elapsed = time.perf_counter() - start
    print(
        f"Timeline extraction {'interrupted' if rate_limited else 'complete'}: "
        f"{success_count} with events, {empty_count} empty/failed, "
        f"{processed_this_run} extracted this run  ({elapsed:.1f}s)"
    )

    if rate_limited:
        remaining = total_pdfs - len(checkpoint)
        print(
            f"\n  Checkpoint saved to {CHECKPOINT_PATH}"
            f"\n  Re-run this script to resume ({remaining} PDFs remaining)."
        )
        sys.exit(1)


def main():
    """Load PDFs, chunk text, extract timelines, create embeddings, and persist FAISS."""
    pdf_files = find_pdf_files(Settings.pdf_dir)
    print(f"Found {len(pdf_files)} PDFs under {Settings.pdf_dir}")

    processor = DocumentProcessor(
        chunk_size=Settings.chunk_size,
        chunk_overlap=Settings.chunk_overlap,
    )
    chunks = processor.process(Settings.pdf_dir)
    print(f"Created {len(chunks)} text chunks")

    # --- Pre-extract timeline events per PDF (with checkpointing) ---
    _enrich_chunks_with_timelines(chunks)

    create_vectorstore(chunks, Settings.vectorstore_dir)
    print(f"Saved FAISS index to {Settings.vectorstore_dir}")
    print(f"Checkpoint retained at {CHECKPOINT_PATH} for future rebuilds.")


if __name__ == "__main__":
    main()
