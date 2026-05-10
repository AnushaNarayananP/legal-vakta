"""Presentation helpers for the SpaceL AI Streamlit UI."""

import re
from pathlib import Path
from typing import Dict


SECTION_TITLES = [
    "Key Insight",
    "Legal Issue",
    "Legal Reasoning",
    "Final Takeaway",
    "Source Evidence",
]

STUDENT_SECTION_TITLES = [
    "Simple Explanation",
    "Legal Concept",
    "Example",
    "Why This Matters",
    "Simplified Source Evidence",
]

SECTION_ICONS = {
    "Key Insight": "💡",
    "Legal Issue": "📌",
    "Legal Reasoning": "⚖️",
    "Final Takeaway": "✅",
    "Source Evidence": "📚",
    "Simple Explanation": "💡",
    "Legal Concept": "📌",
    "Example": "🧩",
    "Why This Matters": "⚖️",
    "Simplified Source Evidence": "📚",
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


def parse_structured_answer(answer: str, titles=None) -> Dict[str, str]:
    """Extract SpaceL AI sections from the model's structured answer."""
    section_titles = list(titles or SECTION_TITLES)
    sections = {title: "" for title in section_titles}
    escaped_titles = "|".join(re.escape(title) for title in section_titles)
    pattern = re.compile(
        r"(?:^|\n)\s*(?:\d+\.\s*)?"
        rf"({escaped_titles})"
        r"\s*:\s*",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(answer or ""))

    for index, match in enumerate(matches):
        raw_title = match.group(1).lower()
        title = next(item for item in section_titles if item.lower() == raw_title)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(answer)
        sections[title] = answer[start:end].strip()

    if not matches and answer:
        fallback_title = "Legal Reasoning" if "Legal Reasoning" in sections else section_titles[0]
        sections[fallback_title] = str(answer).strip()

    return sections


def sort_source_evidence(content: str) -> str:
    """Sort display blocks that begin with Source N in ascending source order."""
    lines = str(content or "").strip().splitlines()
    if not lines:
        return ""

    intro_lines = []
    source_blocks = []
    current_number = None
    current_lines = []
    source_pattern = re.compile(r"\bSource\s*(\d+)\b", re.IGNORECASE)

    for line in lines:
        match = source_pattern.search(line)
        if match:
            if current_lines:
                source_blocks.append((current_number, current_lines))
            current_number = int(match.group(1))
            current_lines = [line]
        elif current_lines:
            current_lines.append(line)
        else:
            intro_lines.append(line)

    if current_lines:
        source_blocks.append((current_number, current_lines))

    if not source_blocks:
        return str(content or "").strip()

    sorted_blocks = sorted(enumerate(source_blocks), key=lambda item: (item[1][0], item[0]))
    output_blocks = []
    intro = "\n".join(line for line in intro_lines if line.strip()).strip()
    if intro:
        output_blocks.append(intro)
    output_blocks.extend("\n".join(block_lines) for _, (_, block_lines) in sorted_blocks)
    return "\n\n".join(output_blocks)


def build_key_insight(sections: Dict[str, str]) -> str:
    """Create a 1-2 line takeaway from the strongest answer section."""
    candidate_text = (
        sections.get("Key Insight")
        or sections.get("Final Takeaway")
        or sections.get("Legal Reasoning")
        or sections.get("Legal Issue")
        or ""
    )

    for line in candidate_text.splitlines():
        cleaned = strip_bullet_prefix(line)
        if cleaned:
            return cleaned

    return "Relevant legal material not found in provided documents."


def get_source_display_metadata(doc) -> Dict[str, str]:
    """Return clean source metadata for UI display."""
    metadata = getattr(doc, "metadata", {}) or {}
    source = metadata.get("source", "")
    file_name = metadata.get("file_name") or Path(str(source)).name
    return {
        "pdf_name": file_name or "Not available",
        "case_year": str(metadata.get("case_year") or "Not available"),
        "page": str(metadata.get("page") if metadata.get("page") is not None else "Not available"),
        "relevance_reason": str(metadata.get("relevance_reason") or "Not available"),
    }


def format_case_label(doc, source_number: int) -> str:
    """Build the professional source label shown in expanders."""
    display = get_source_display_metadata(doc)
    return (
        f"Source {source_number} — Supreme Court Judgment | "
        f"Case Year: {display['case_year']} | Page: {display['page']}"
    )


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
