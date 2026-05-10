from dataclasses import dataclass

from src.ui.formatting import (
    SECTION_TITLES,
    STUDENT_SECTION_TITLES,
    build_key_insight,
    emphasize_legal_keywords,
    format_case_label,
    get_source_display_metadata,
    parse_structured_answer,
    sort_source_evidence,
)


@dataclass
class Document:
    page_content: str
    metadata: dict


def test_parse_structured_answer_extracts_expected_sections():
    answer = """
1. Key Insight:
- Benefit of doubt may apply when prosecution evidence is weak.

2. Legal Issue:
- Whether benefit of doubt applied.

3. Legal Reasoning:
- The Court found contradictions.

4. Final Takeaway:
- The conviction may be unsafe if contradictions remain unresolved.

5. Source Evidence:
- "The prosecution failed to prove the case."
"""

    sections = parse_structured_answer(answer)

    assert list(sections.keys()) == SECTION_TITLES
    assert sections["Key Insight"] == "- Benefit of doubt may apply when prosecution evidence is weak."
    assert sections["Legal Issue"] == "- Whether benefit of doubt applied."
    assert sections["Final Takeaway"] == "- The conviction may be unsafe if contradictions remain unresolved."
    assert sections["Source Evidence"] == '- "The prosecution failed to prove the case."'


def test_parse_structured_answer_extracts_student_sections():
    answer = """
1. Simple Explanation:
- The court gives the accused the benefit of doubt when proof is weak.

2. Legal Concept:
- Proof must be strong enough to support conviction.

3. Example:
- The documents do not provide one.

4. Why This Matters:
- It helps students understand appellate review.

5. Simplified Source Evidence:
- Source 1 supports this point.
"""

    sections = parse_structured_answer(answer, titles=STUDENT_SECTION_TITLES)

    assert list(sections.keys()) == STUDENT_SECTION_TITLES
    assert sections["Simple Explanation"].startswith("- The court gives")
    assert sections["Simplified Source Evidence"] == "- Source 1 supports this point."


def test_sort_source_evidence_orders_numbered_source_blocks():
    content = """
- Source 2: second quote.
  continuation for source two.
- Source 5: fifth quote.
- Source 1: first quote.
- Source 3: third quote.
"""

    result = sort_source_evidence(content)

    assert result.index("Source 1") < result.index("Source 2")
    assert result.index("Source 2") < result.index("Source 3")
    assert result.index("Source 3") < result.index("Source 5")
    assert "continuation for source two" in result


def test_build_key_insight_prefers_possible_legal_direction():
    sections = {
        "Legal Issue": "- Whether conviction is sustainable.",
        "Final Takeaway": "- The retrieved case suggests benefit of doubt where evidence is contradictory.",
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
        "Source 1 — Supreme Court Judgment | Case Year: 2020 | Page: 12"
    )


def test_format_case_label_falls_back_for_missing_metadata():
    doc = Document(page_content="Snippet.", metadata={})

    assert format_case_label(doc, source_number=3) == (
        "Source 3 — Supreme Court Judgment | Case Year: Not available | Page: Not available"
    )


def test_get_source_display_metadata_cleans_missing_values():
    doc = Document(page_content="Snippet.", metadata={"source": "C:/cases/example.pdf"})

    display = get_source_display_metadata(doc)

    assert display == {
        "pdf_name": "example.pdf",
        "case_year": "Not available",
        "page": "Not available",
        "relevance_reason": "Not available",
    }


def test_emphasize_legal_keywords_bolds_demo_terms():
    text = "The accused was acquitted after benefit of doubt on conviction."

    result = emphasize_legal_keywords(text)

    assert "**benefit of doubt**" in result
    assert "**acquitted**" in result
    assert "**conviction**" in result
