"""Structured LLM extraction of chronological events from legal text.

This module uses Pydantic models and the OpenAI SDK ``response_format``
(JSON mode) via the existing OpenRouter client to extract timeline events
from a court-document text excerpt.  The extraction function is wrapped
with ``@st.cache_data`` so that toggling the timeline UI on/off never
triggers duplicate LLM calls.

It is deliberately isolated from the UI layer — the only coupling is the
shared ``get_openrouter_client()`` factory and environment variables.
"""

import json
import logging
from typing import List

import streamlit as st
from pydantic import BaseModel, Field

from src.llm.openrouter_client import get_openrouter_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class TimelineEvent(BaseModel):
    """A single chronological milestone extracted from legal text."""

    date: str = Field(
        ...,
        description=(
            "The date or time reference exactly as it appears in the text, "
            "e.g. 'Pre-2013', '25-11-2013', 'November 2013', '2008'."
        ),
    )
    event: str = Field(
        ...,
        description="A brief 1-sentence summary of the milestone or event.",
    )


class TimelinePayload(BaseModel):
    """Container for a list of extracted timeline events."""

    events: List[TimelineEvent] = Field(
        default_factory=list,
        description="Chronologically ordered list of events. Empty if none found.",
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a legal document analyst. Analyze the provided legal text "
    "excerpt from a court document. Extract any historical dates, trial "
    "phases, filings, notices, or relevant factual events into a strictly "
    "chronological sequence. Only extract items explicitly referenced in "
    "the text.\n\n"
    "Return ONLY valid JSON matching this schema:\n"
    '{"events": [{"date": "<date string>", "event": "<brief summary>"}]}\n\n'
    "Rules:\n"
    "- If no chronological events are found, return {\"events\": []}.\n"
    "- Keep each event summary under 20 words.\n"
    "- Dates must appear exactly as written in the text.\n"
    "- Order events from earliest to latest.\n"
    "- Maximum 8 events.\n"
    "- Do NOT fabricate events or dates not present in the text."
)


# ---------------------------------------------------------------------------
# Extraction function (cached)
# ---------------------------------------------------------------------------

# The model used for fast, cheap timeline extraction.
_TIMELINE_MODEL = "openai/gpt-4o-mini"


@st.cache_data(show_spinner=False)
def extract_timeline_from_text(source_text: str) -> list:
    """Extract chronological events from *source_text* via an LLM call.

    Parameters
    ----------
    source_text : str
        The ``page_content`` from a retrieved source document.

    Returns
    -------
    list[dict]
        Each dict has keys ``"date"`` and ``"event"``.  Returns an empty
        list when no events are found or if the API call fails.
    """
    if not source_text or len(source_text.strip()) < 30:
        return []

    try:
        client = get_openrouter_client()

        response = client.chat.completions.create(
            model=_TIMELINE_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": source_text[:3000]},  # cap input tokens
            ],
            temperature=0.0,
            max_tokens=800,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content.strip()
        payload = TimelinePayload.model_validate(json.loads(raw_content))
        return [ev.model_dump() for ev in payload.events]

    except Exception:
        logger.exception("Timeline extraction failed")
        return []
