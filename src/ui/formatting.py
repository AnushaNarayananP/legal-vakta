"""Presentation helpers for the Legal Vakta Streamlit UI."""

import re
from pathlib import Path
from typing import Dict


SECTION_TITLES = [
    "Legal Issue",
    "Relevant Case Context",
    "Legal Reasoning",
    "Possible Legal Direction",
    "Source Evidence",
]

SECTION_ICONS = {
    "Legal Issue": "📌",
    "Relevant Case Context": "📂",
    "Legal Reasoning": "⚖️",
    "Possible Legal Direction": "📊",
    "Source Evidence": "📖",
}

LEGAL_KEYWORDS = [
    "benefit of doubt",
    "acquitted",
    "acquittal",
    "conviction",
    "sentence",
    "evidence",
    "prosecution",
    "appeal",
]


def normalize_text(text: str) -> str:
    """Collapse excess whitespace while keeping content readable."""
    return re.sub(r"\s+", " ", str(text or "")).strip()


def strip_bullet_prefix(text: str) -> str:
    """Remove common bullet/number prefixes for compact insight text."""
    return re.sub(r"^[-*\d.\s]+", "", text).strip()


def parse_structured_answer(answer: str) -> Dict[str, str]:
    """Extract Legal Vakta sections from the model's structured answer."""
    sections = {title: "" for title in SECTION_TITLES}
    pattern = re.compile(
        r"(?:^|\n)\s*(?:\d+\.\s*)?"
        r"(Legal Issue|Relevant Case Context|Legal Reasoning|Possible Legal Direction|Source Evidence)"
        r"\s*:\s*",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(answer or ""))

    for index, match in enumerate(matches):
        raw_title = match.group(1).lower()
        title = next(item for item in SECTION_TITLES if item.lower() == raw_title)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(answer)
        sections[title] = answer[start:end].strip()

    if not matches and answer:
        sections["Legal Reasoning"] = str(answer).strip()

    return sections


def build_key_insight(sections: Dict[str, str]) -> str:
    """Create a 1-2 line takeaway from the strongest answer section."""
    candidate_text = (
        sections.get("Possible Legal Direction")
        or sections.get("Legal Reasoning")
        or sections.get("Legal Issue")
        or ""
    )

    for line in candidate_text.splitlines():
        cleaned = strip_bullet_prefix(line)
        if cleaned:
            return cleaned

    return "Relevant legal material not found in provided documents."


def format_case_label(doc, source_number: int) -> str:
    """Build the professional source label shown in expanders."""
    metadata = getattr(doc, "metadata", {}) or {}
    source = metadata.get("source", "")
    source_id = metadata.get("source_id") or source_number
    file_name = metadata.get("file_name") or Path(str(source)).name or "Unknown PDF"
    year = metadata.get("case_year") or "Unknown year"
    page = metadata.get("page")
    page_label = page if page is not None else "Unknown page"
    return f"Source {source_id} | PDF: {file_name} | Case year: {year} | Page: {page_label}"


def emphasize_legal_keywords(text: str) -> str:
    """Bold important legal keywords inside snippets."""
    highlighted = str(text or "")
    for keyword in LEGAL_KEYWORDS:
        highlighted = re.sub(
            rf"\b({re.escape(keyword)})\b",
            r"**\1**",
            highlighted,
            flags=re.IGNORECASE,
        )
    return highlighted


def clean_snippet(text: str, max_chars: int = 1200) -> str:
    """Prepare a short snippet for an expander."""
    snippet = normalize_text(text)
    if len(snippet) > max_chars:
        snippet = f"{snippet[:max_chars].rstrip()}..."
    return emphasize_legal_keywords(snippet)
