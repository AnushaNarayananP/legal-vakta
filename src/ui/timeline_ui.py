"""Source Event Timeline rendering for SpaceL AI evidence cards.

Approach 1 — Pre-Extraction & Metadata Storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Timeline data is extracted during the document ingestion pipeline and
stored as ``pre_extracted_timeline`` inside each judgment's metadata.
This module simply **reads** that pre-saved list and renders it using
native Streamlit widgets.

**No iframes, no ``st.iframe()``, no LLM calls at render
time.**  All layout is handled through ``st.columns`` + ``st.markdown``,
ensuring the timeline scales fluidly within expander cards at any screen
width — no scrollbars, no cropping, no overlapping text.

Isolation guarantees:
  - Per-source session-state keys scoped as ``timeline_toggle_{source_id}``
  - No global state, no external API calls, no side-effects
"""

from typing import Dict, List

import streamlit as st


# ---------------------------------------------------------------------------
# Native-Streamlit timeline renderer (no iframes)
# ---------------------------------------------------------------------------

def _render_timeline_nodes(events: List[Dict[str, str]]) -> None:
    """Render timeline events as native Streamlit columns with a CSS bar.

    Each event becomes one ``st.columns`` cell containing:
      - A dot marker (via ``st.markdown``)
      - The date in bold
      - The event description as a caption

    A single injected ``<style>`` block draws a horizontal connecting
    line behind the dots.  Because the line is drawn via CSS on a
    full-width Streamlit div (not an iframe), it scales naturally to
    100 % of the container.
    """

    # -- Inject the connecting-bar CSS once per render --
    st.markdown(
        """
        <style>
        .tl-bar {
            position: relative;
            width: 100%;
            height: 2px;
            background: linear-gradient(90deg, #94a3b8, #64748b, #94a3b8);
            margin: 0 0 12px 0;
            border-radius: 1px;
        }
        .tl-dot-marker {
            display: flex;
            justify-content: center;
            margin-bottom: 6px;
        }
        .tl-dot-marker span {
            display: inline-block;
            width: 13px;
            height: 13px;
            border-radius: 50%;
            background: #475569;
            border: 2.5px solid #e2e8f0;
            box-shadow: 0 0 0 2px #475569;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # -- Horizontal connecting bar (full-width, no iframe) --
    st.markdown('<div class="tl-bar"></div>', unsafe_allow_html=True)

    # -- Dynamic columns: one per event --
    cols = st.columns(len(events))

    for col, ev in zip(cols, events):
        with col:
            # Dot marker
            st.markdown(
                '<div class="tl-dot-marker"><span></span></div>',
                unsafe_allow_html=True,
            )
            # Date — bold, centered
            st.markdown(
                f"<p style='text-align:center; font-size:.82rem; "
                f"font-weight:700; color:#1e293b; margin:0 0 2px 0; "
                f"line-height:1.25; white-space:normal;'>"
                f"{ev['date']}</p>",
                unsafe_allow_html=True,
            )
            # Event description — muted caption, wrapping naturally
            st.caption(ev["event"])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_stored_timeline(
    source_id: str,
    timeline_data: list,
) -> None:
    """Render a pre-extracted event timeline for one source card.

    This is the single entry-point called by ``source_evidence_ui.py``.
    It reads the toggle state from ``st.session_state`` via the key
    ``f"timeline_toggle_{source_id}"``.  When the toggle is **on**, it
    renders the pre-saved data as native Streamlit columns, or shows a
    clean "no events found" message.

    Parameters
    ----------
    source_id : str
        A unique identifier for this source card (e.g. ``"1_30182.pdf"``).
    timeline_data : list
        Pre-extracted list of ``{"date": "...", "event": "..."}`` dicts
        from ``doc.metadata["pre_extracted_timeline"]``.  May be ``[]``.
    """
    toggle_key = f"timeline_toggle_{source_id}"

    # If the toggle doesn't exist yet or is False, nothing to render.
    if not st.session_state.get(toggle_key, False):
        return

    # -- Section header --
    st.markdown(
        '<div style="border:1px solid #e2e8f0; border-radius:8px; '
        'padding:10px 8px 4px 8px; margin:6px 0 10px 0; '
        'background:#f8fafc;">'
        '<span style="font-size:.78rem; font-weight:600; '
        'color:#475569; letter-spacing:.02em;">'
        '🕐 SOURCE EVENT TIMELINE</span></div>',
        unsafe_allow_html=True,
    )

    # -- Render results --
    if timeline_data:
        _render_timeline_nodes(timeline_data)
    else:
        st.caption(
            "No chronological timeline events found for this judgment record."
        )
