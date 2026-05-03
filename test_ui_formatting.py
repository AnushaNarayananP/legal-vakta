from dataclasses import dataclass

from src.ui.formatting import (
    SECTION_TITLES,
    build_key_insight,
    emphasize_legal_keywords,
    format_case_label,
    parse_structured_answer,
)


@dataclass
class Document:
    page_content: str
    metadata: dict


def test_parse_structured_answer_extracts_expected_sections():
    answer = """
1. Legal Issue:
- Whether benefit of doubt applied.

2. Relevant Case Context:
- The appeal challenged conviction.

3. Legal Reasoning:
- The Court found contradictions.

4. Possible Legal Direction:
- Benefit of doubt may follow.

5. Source Evidence:
- "The prosecution failed to prove the case."
"""

    sections = parse_structured_answer(answer)

    assert list(sections.keys()) == SECTION_TITLES
    assert sections["Legal Issue"] == "- Whether benefit of doubt applied."
    assert sections["Source Evidence"] == '- "The prosecution failed to prove the case."'


def test_build_key_insight_prefers_possible_legal_direction():
    sections = {
        "Legal Issue": "- Whether conviction is sustainable.",
        "Possible Legal Direction": "- The retrieved case suggests benefit of doubt where evidence is contradictory.",
    }

    assert build_key_insight(sections) == (
        "The retrieved case suggests benefit of doubt where evidence is contradictory."
    )


def test_format_case_label_uses_source_number_filename_year_and_page():
    doc = Document(
        page_content="Enough text for a useful snippet.",
        metadata={"file_name": "case.pdf", "case_year": 2020, "page": 12},
    )

    assert format_case_label(doc, source_number=1) == (
        "Source 1 | PDF: case.pdf | Case year: 2020 | Page: 12"
    )


def test_format_case_label_falls_back_for_missing_metadata():
    doc = Document(page_content="Snippet.", metadata={})

    assert format_case_label(doc, source_number=3) == (
        "Source 3 | PDF: Unknown PDF | Case year: Unknown year | Page: Unknown page"
    )


def test_emphasize_legal_keywords_bolds_demo_terms():
    text = "The accused was acquitted after benefit of doubt on conviction."

    result = emphasize_legal_keywords(text)

    assert "**benefit of doubt**" in result
    assert "**acquitted**" in result
    assert "**conviction**" in result
