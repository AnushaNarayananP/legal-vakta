"""Redesigned Source Evidence card rendering for SpaceL AI.

This module owns the presentation of retrieved source documents.
It is deliberately isolated from retrieval / ranking / LLM prompt logic.
The only external data dependency is the selected_judgments CSV used to
enrich per-source metadata at display time.
"""

import html as html_mod
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st


from src.config import Settings
from src.ui.formatting import clean_snippet
from src.ui.timeline_ui import render_stored_timeline

# ---------------------------------------------------------------------------
# CSV metadata lookup
# ---------------------------------------------------------------------------

_SELECTED_CSV_PATH = Settings.processed_dir / "selected_judgments.csv"


@st.cache_data(show_spinner=False)
def _load_csv_rows(csv_path: str) -> Dict[str, dict]:
    """Load the selected-judgments CSV and index rows by PDF filename.

    Returns a dict mapping PDF filename (e.g. ``"30182.pdf"``) to the full
    CSV row as a plain dict.  Filenames are extracted from the ``temp_link``
    column (the trailing path component).
    """
    path = Path(csv_path)
    if not path.exists():
        return {}

    try:
        df = pd.read_csv(path)
    except Exception:
        return {}

    lookup: Dict[str, dict] = {}
    for _, row in df.iterrows():
        temp_link = row.get("temp_link")
        if pd.isna(temp_link):
            continue
        pdf_filename = Path(str(temp_link).replace("\\", "/").strip()).name
        if pdf_filename:
            lookup[pdf_filename] = row.to_dict()
    return lookup


def load_judgment_metadata_lookup() -> Dict[str, dict]:
    """Public entry-point — returns the cached CSV lookup dict."""
    return _load_csv_rows(str(_SELECTED_CSV_PATH))


# ---------------------------------------------------------------------------
# Metadata extraction helpers
# ---------------------------------------------------------------------------

def extract_case_name(csv_row: Optional[dict]) -> str:
    """Build ``"Petitioner v. Respondent"`` from CSV columns.

    Returns an empty string when the data is unavailable so callers can
    fall back gracefully.
    """
    if csv_row is None:
        return ""
    pet = str(csv_row.get("pet") or "").strip()
    res = str(csv_row.get("res") or "").strip()
    if not pet and not res:
        return ""
    if pet and res:
        return f"{_title_case_party(pet)} v. {_title_case_party(res)}"
    return _title_case_party(pet or res)


def _title_case_party(name: str) -> str:
    """Convert ``"RAMESH KUMAR"`` → ``"Ramesh Kumar"``."""
    if not name:
        return name
    # Preserve common legal abbreviations that should stay uppercase.
    abbreviations = {"CBI", "NIA", "NCB", "SBI"}
    parts = name.split()
    result = []
    for part in parts:
        # Strip common suffixes like "TH:CBI" → keep "CBI"
        if part.upper() in abbreviations:
            result.append(part.upper())
        elif ":" in part:
            # e.g. "TH:CBI" → keep as-is after title-casing the prefix
            sub = part.split(":", 1)
            result.append(sub[0].title() + ":" + sub[1].upper())
        else:
            result.append(part.title())
    return " ".join(result)


def build_citation_line(csv_row: Optional[dict], case_year: str) -> str:
    """Build a formatted citation string from CSV metadata.

    Format: ``Supreme Court of India · Crl.A. No.-000186 - 2008 · Decided 07-05-2010``
    Returns empty string when no usable data exists.
    """
    if csv_row is None:
        return ""
    parts = ["Supreme Court of India"]

    case_no = str(csv_row.get("case_no") or "").strip()
    if case_no:
        parts.append(case_no)

    judgment_date = str(csv_row.get("judgment_dates") or "").strip()
    if judgment_date:
        parts.append(f"Decided {judgment_date}")
    elif case_year and case_year != "Not available":
        parts.append(f"Year {case_year}")

    return " · ".join(parts) if len(parts) > 1 else ""


def _get_bench_display(csv_row: Optional[dict]) -> str:
    """Extract a clean bench (judges) string."""
    if csv_row is None:
        return ""
    bench = str(csv_row.get("bench") or "").strip().rstrip(",").strip()
    if not bench:
        return ""
    # Clean up double commas and trailing whitespace from raw CSV
    bench = re.sub(r",\s*,", ",", bench)
    bench = bench.strip(", ")
    return bench


# ---------------------------------------------------------------------------
# Card rendering
# ---------------------------------------------------------------------------

def render_source_evidence_card(
    doc,
    source_number: int,
    metadata_lookup: Dict[str, dict],
) -> None:
    """Render one redesigned source evidence card inside a Streamlit expander.

    Parameters
    ----------
    doc : langchain Document
        A single retrieved document with ``page_content`` and ``metadata``.
    source_number : int
        1-based index shown to the user.
    metadata_lookup : dict
        Mapping of PDF filename → CSV row dict, from
        :func:`load_judgment_metadata_lookup`.
    """
    meta = getattr(doc, "metadata", {}) or {}
    file_name = meta.get("file_name") or Path(str(meta.get("source", ""))).name
    case_year = str(meta.get("case_year") or "Not available")
    raw_page = meta.get("page")
    page_display = str(int(raw_page) + 1) if raw_page is not None else "N/A"

    # Enrich with CSV data
    csv_row = metadata_lookup.get(file_name)
    case_name = extract_case_name(csv_row)
    citation = build_citation_line(csv_row, case_year)
    bench = _get_bench_display(csv_row)

    # Build expander label — case name when available, else filename
    if case_name:
        expander_label = f"Source {source_number} — {case_name}"
    else:
        expander_label = f"Source {source_number} — {file_name} ({case_year})"

    with st.expander(expander_label):
        # -- Case name heading (if available) --
        if case_name:
            st.markdown(f"#### {case_name}")

        # -- Citation line --
        if citation:
            st.markdown(
                f'<div class="source-meta" style="font-size:.93rem;">'
                f"⚖️ {html_mod.escape(citation)}</div>",
                unsafe_allow_html=True,
            )

        # -- Bench --
        if bench:
            st.caption(f"Bench: {bench}")

        # -- Page anchor --
        st.markdown(f"**Page {page_display}**")

        # -- File reference (secondary) --
        if case_name:
            # Show filename as a muted secondary line since case name is primary
            st.caption(f"📄 {file_name}")

        # -- Timeline (conditionally visible — reads pre-extracted data) --
        source_id = f"{source_number}_{file_name}"
        pre_timeline = meta.get("pre_extracted_timeline", [])

        # Ensure the timeline always ends with the Supreme Court's final
        # decision date so the horizontal bar feels visually complete.
        if pre_timeline and not any(
            "supreme court" in node.get("event", "").lower()
            for node in pre_timeline
        ):
            decision_date = (
                str(csv_row.get("judgment_dates", "")).strip()
                if csv_row
                else ""
            ) or "Final"
            pre_timeline = [*pre_timeline, {
                "date": decision_date,
                "event": "Supreme Court of India delivers the final judgment on appeal.",
            }]

        render_stored_timeline(
            source_id=source_id,
            timeline_data=pre_timeline,
        )

        # -- Snippet text --
        raw_page_content = getattr(doc, "page_content", "")
        # NOTE: Highlighting uses keyword-overlap bolding from formatting.py
        # (emphasize_legal_keywords). This is NOT retrieval-flagged span
        # highlighting — the retriever/LLM does not produce highlight
        # offsets. The keyword list is a fixed set of common legal terms.
        snippet_text = clean_snippet(raw_page_content)
        if snippet_text:
            st.info(snippet_text)
        else:
            st.caption("Snippet not available.")

        # -- "Cited for:" stub --
        # TODO: "Cited for" one-line reasoning is not currently generated
        # by the LLM pipeline. To enable it, the system prompt in
        # graph_builder.py (LEGAL_RESEARCH_SYSTEM_PROMPT) would need to
        # request a per-source "Cited for: <reason>" line in the Source
        # Evidence section. The generate_answer() method would then parse
        # these per-source reasons and attach them to each retrieved doc's
        # metadata (e.g. as doc.metadata["cited_for"]) before returning
        # the RAGState. Until that upstream change is made, this field
        # is intentionally omitted from the card.
        relevance = str(meta.get("relevance_reason") or "")
        if relevance and relevance != "Not available":
            st.markdown(f"**Cited for:** {relevance}")

        # -- Action row --
        # Always show a 3-column layout so the timeline toggle is always
        # visible.
        action_col1, action_col2, action_col3 = st.columns(3)

        with action_col1:
            _render_open_judgment_button(meta, source_number)

        with action_col2:
            if citation:
                _render_copy_citation_button(citation, source_number)

        with action_col3:
            st.toggle(
                "📊 Timeline View",
                key=f"timeline_toggle_{source_id}",
            )


def _render_open_judgment_button(meta: dict, source_number: int) -> None:
    """Render a download button for the source PDF when the file exists."""
    source_path = meta.get("source", "")
    if not source_path:
        return
    pdf_path = Path(source_path)
    if not pdf_path.exists():
        st.caption("PDF not available locally.")
        return

    file_name = meta.get("file_name") or pdf_path.name
    try:
        pdf_bytes = pdf_path.read_bytes()
        st.download_button(
            label="📥 Open Full Judgment",
            data=pdf_bytes,
            file_name=file_name,
            mime="application/pdf",
            key=f"download_pdf_{source_number}_{file_name}",
            use_container_width=True,
        )
    except Exception:
        st.caption("Could not read PDF file.")


def _render_copy_citation_button(citation: str, source_number: int) -> None:
    """Render a button that copies the citation text to the clipboard.

    Uses a small JS snippet via ``st.iframe``, consistent with
    the existing ``embed_inline_html`` pattern used elsewhere in the app.
    """
    safe_citation = html_mod.escape(citation).replace("'", "\\'")
    button_id = f"copy_cite_{source_number}"
    html_snippet = f"""
    <button id="{button_id}"
            onclick="
                navigator.clipboard.writeText('{safe_citation}')
                    .then(function() {{
                        document.getElementById('{button_id}').innerText = '✅ Copied!';
                        setTimeout(function() {{
                            document.getElementById('{button_id}').innerText = '📋 Copy Citation';
                        }}, 1500);
                    }});
            "
            style="
                width: 100%;
                padding: .45rem .75rem;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                background: #ffffff;
                color: #374151;
                font-size: .88rem;
                cursor: pointer;
                transition: background .15s;
            "
            onmouseover="this.style.background='#f9fafb';"
            onmouseout="this.style.background='#ffffff';">
        📋 Copy Citation
    </button>
    """
    st.iframe(html_snippet, height=42)


# NOTE: The _render_timeline_toggle helper has been removed.
# The timeline toggle is now rendered inline as st.toggle() in the
# action row inside render_source_evidence_card().


# ---------------------------------------------------------------------------
# Section-level renderer (replaces render_retrieved_documents body)
# ---------------------------------------------------------------------------

def render_source_evidence_section(docs: List) -> None:
    """Render the full Source Evidence section with redesigned cards.

    This is the drop-in replacement for the body of
    ``app.render_retrieved_documents()``.  It handles the section heading,
    empty-state, and iterates over documents using the new card renderer.
    """
    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
    st.divider()
    st.markdown("### 📚 Source Evidence")

    if not docs:
        st.info("No documents retrieved.")
        return

    metadata_lookup = load_judgment_metadata_lookup()

    for source_number, doc in enumerate(docs, start=1):
        render_source_evidence_card(doc, source_number, metadata_lookup)
