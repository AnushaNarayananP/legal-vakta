import pandas as pd

from dataset_descreibe import (
    build_balanced_mvp_dataset,
    build_curated_dataset,
    extract_case_year,
    preview_random_cases,
)


def test_extract_case_year_reads_valid_year_from_case_no():
    assert extract_case_year("Crl.A. No.-000523-000523 - 2024") == 2024
    assert extract_case_year("Diary 1999 / Crl.A.") == 1999
    assert pd.isna(extract_case_year("Crl.A. No.-000523"))
    assert pd.isna(extract_case_year(None))


def test_build_curated_dataset_filters_and_cleans_cases():
    df = pd.DataFrame(
        {
            "diary_no": [1, 2, 3, 4, 5, 6, 7],
            "Judgement_type": ["J"] * 7,
            "case_no": [
                "Crl.A. No.-000001-000001 - 2008",
                "crl.a. No.-000002-000002 - 2023",
                "Crl.A. No.-000003-000003 - 2024",
                "C.A. No.-000004-000004 - 2020",
                "Crl.A. No.-000005-000005",
                "Crl.A. No.-000001-000001 - 2008",
                "Crl.A. No.-000006-000006 - 2015",
            ],
            "pet": ["p"] * 7,
            "res": ["r"] * 7,
            "pet_adv": ["pa"] * 7,
            "res_adv": ["ra"] * 7,
            "bench": ["b"] * 7,
            "judgement_by": ["j"] * 7,
            "judgment_dates": ["01-01-2020"] * 7,
            "temp_link": [
                "supremecourt/2008/link-1.pdf",
                "supremecourt/2023/link-2.pdf",
                "supremecourt/2024/link-3.pdf",
                "supremecourt/2020/link-4.pdf",
                "supremecourt/link-5.pdf",
                "supremecourt/2008/duplicate.pdf",
                None,
            ],
            "language": [None, pd.NA, None, None, None, None, None],
        }
    )

    result = build_curated_dataset(df)

    assert result["case_no"].tolist() == [
        "Crl.A. No.-000001-000001 - 2008",
        "crl.a. No.-000002-000002 - 2023",
        "Crl.A. No.-000003-000003 - 2024",
    ]
    assert result["case_year"].tolist() == [2008, 2023, 2024]


def test_build_curated_dataset_excludes_non_missing_language_and_vernacular_links():
    df = pd.DataFrame(
        {
            "case_no": [
                "Crl.A. No.-000001-000001 - 2020",
                "Crl.A. No.-000002-000002 - 2020",
                "Crl.A. No.-000003-000003 - 2020",
            ],
            "temp_link": [
                "supremecourt/2020/link-1.pdf",
                "supremecourt/2020/link-2.pdf",
                "supremecourt/2020/vernacular/link-3.pdf",
            ],
            "language": [None, "", None],
        }
    )

    result = build_curated_dataset(df)

    assert result["case_no"].tolist() == ["Crl.A. No.-000001-000001 - 2020"]


def test_build_curated_dataset_keeps_all_quality_rows_without_sampling():
    df = pd.DataFrame(
        {
            "case_no": [
                f"Crl.A. No.-{index:06d}-{index:06d} - 2020" for index in range(20)
            ],
            "case_year": [2020] * 20,
            "temp_link": [f"supremecourt/2020/link-{index}.pdf" for index in range(20)],
            "language": [None] * 20,
        }
    )

    result = build_curated_dataset(df)

    assert len(result) == 20


def test_preview_random_cases_returns_reproducible_subset():
    df = pd.DataFrame(
        {
            "case_no": [f"Crl.A. No.-{index:06d}-{index:06d} - 2020" for index in range(10)],
            "case_year": [2020] * 10,
            "temp_link": [f"link-{index}.pdf" for index in range(10)],
        }
    )

    result = preview_random_cases(df, count=5, random_state=42)

    assert len(result) == 5
    assert result["case_no"].tolist() == preview_random_cases(
        df, count=5, random_state=42
    )["case_no"].tolist()


def test_build_balanced_mvp_dataset_filters_year_range_and_caps_at_15():
    df = pd.DataFrame(
        {
            "case_no": [
                f"Crl.A. No.-{index:06d}-{index:06d} - 2020" for index in range(20)
            ]
            + [f"Crl.A. No.-{index:06d}-{index:06d} - 2021" for index in range(3)]
            + [
                "Crl.A. No.-999998-999998 - 2007",
                "Crl.A. No.-999999-999999 - 2024",
            ],
            "case_year": [2020] * 20 + [2021] * 3 + [2007, 2024],
            "temp_link": [f"link-{index}.pdf" for index in range(25)],
        }
    )

    result = build_balanced_mvp_dataset(df)

    assert len(result) == 18
    assert result["case_year"].value_counts().sort_index().to_dict() == {
        2020: 15,
        2021: 3,
    }
