from pathlib import Path
import shutil

import pandas as pd

from scripts.organize_selected_pdfs import (
    copy_selected_pdfs,
    find_source_pdf,
    get_pdf_filename,
)


def test_get_pdf_filename_extracts_basename_from_temp_link():
    temp_link = "supremecourt/2023/31911/31911_2023_15_1501_50375_Judgement_13-Feb-2024.pdf"

    assert (
        get_pdf_filename(temp_link)
        == "31911_2023_15_1501_50375_Judgement_13-Feb-2024.pdf"
    )
    assert get_pdf_filename("jonew/judis/36329.pdf") == "36329.pdf"
    assert get_pdf_filename(None) == ""


def test_find_source_pdf_supports_diary_prefixed_sanitized_names():
    test_root = Path("test_artifacts") / "find_source_pdf"
    if test_root.exists():
        shutil.rmtree(test_root)

    source_dir = test_root / "pdfs"
    source_dir.mkdir(parents=True)
    expected = source_dir / "1150-2007___jonew__judis__36329.pdf"
    expected.write_text("pdf", encoding="utf-8")

    result = find_source_pdf(
        source_pdf_dir=source_dir,
        pdf_filename="36329.pdf",
        temp_link="jonew/judis/36329.pdf",
        diary_no="1150-2007",
    )

    assert result == expected

    shutil.rmtree(test_root)


def test_copy_selected_pdfs_copies_found_files_and_records_missing():
    test_root = Path("test_artifacts") / "organize_selected_pdfs"
    if test_root.exists():
        shutil.rmtree(test_root)

    csv_path = test_root / "selected_judgments.csv"
    source_dir = test_root / "pdfs"
    destination_dir = test_root / "data" / "pdfs"
    missing_csv_path = test_root / "data" / "processed" / "missing_pdfs.csv"

    source_dir.mkdir(parents=True)
    (source_dir / "found.pdf").write_text("pdf", encoding="utf-8")

    pd.DataFrame(
        {
            "temp_link": [
                "supremecourt/2020/1/found.pdf",
                "supremecourt/2021/2/missing.pdf",
            ],
            "case_year": [2020, 2021],
            "diary_no": ["1-2020", "2-2021"],
            "case_no": [
                "Crl.A. No.-000001-000001 - 2020",
                "Crl.A. No.-000002-000002 - 2021",
            ],
        }
    ).to_csv(csv_path, index=False)

    summary = copy_selected_pdfs(
        csv_path=csv_path,
        source_pdf_dir=source_dir,
        destination_pdf_dir=destination_dir,
        missing_csv_path=missing_csv_path,
    )

    assert summary["total_rows"] == 2
    assert summary["copied"] == 1
    assert summary["missing"] == 1
    assert (destination_dir / "2020" / "found.pdf").exists()
    assert pd.read_csv(missing_csv_path)["pdf_filename"].tolist() == ["missing.pdf"]

    shutil.rmtree(test_root)
