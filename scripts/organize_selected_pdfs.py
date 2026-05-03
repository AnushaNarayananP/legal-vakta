"""Copy selected judgment PDFs into data/pdfs/<case_year>/.

The selected metadata CSV stores PDF paths in temp_link. This script extracts
the PDF filename, finds it in the root-level pdfs/ folder, and copies only the
selected files into the final RAG data layout.
"""

from pathlib import Path
import shutil

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "selected_judgments.csv"
DEFAULT_SOURCE_PDF_DIR = PROJECT_ROOT / "pdfs"
DEFAULT_DESTINATION_PDF_DIR = PROJECT_ROOT / "data" / "pdfs"
DEFAULT_MISSING_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "missing_pdfs.csv"


def get_pdf_filename(temp_link):
    """Extract the PDF filename from a temp_link value."""
    if pd.isna(temp_link):
        return ""

    normalized_link = str(temp_link).replace("\\", "/").strip()
    if not normalized_link:
        return ""

    return Path(normalized_link).name


def get_sanitized_pdf_filename(temp_link):
    """Build the sanitized filename format used by the existing root pdfs/ folder."""
    if pd.isna(temp_link):
        return ""

    normalized_link = str(temp_link).replace("\\", "/").strip()
    if not normalized_link:
        return ""

    return normalized_link.replace("/", "__")


def ensure_folder(path):
    """Create a folder if it does not exist."""
    folder = Path(path)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def find_source_pdf(source_pdf_dir, pdf_filename, temp_link, diary_no=None):
    """Find a selected PDF in the source folder by filename or sanitized link name."""
    source_dir = Path(source_pdf_dir)

    direct_match = source_dir / pdf_filename
    if direct_match.exists():
        return direct_match

    sanitized_link = get_sanitized_pdf_filename(temp_link)
    candidate_names = []

    if sanitized_link:
        candidate_names.append(sanitized_link)
        candidate_names.append(f"-0___{sanitized_link}")

    if not pd.isna(diary_no) and str(diary_no).strip() and sanitized_link:
        candidate_names.insert(0, f"{str(diary_no).strip()}___{sanitized_link}")

    for candidate_name in candidate_names:
        candidate_path = source_dir / candidate_name
        if candidate_path.exists():
            return candidate_path

    recursive_matches = list(source_dir.glob(f"**/{pdf_filename}"))
    if recursive_matches:
        return recursive_matches[0]

    for candidate_name in candidate_names:
        sanitized_recursive_matches = list(source_dir.glob(f"**/{candidate_name}"))
        if sanitized_recursive_matches:
            return sanitized_recursive_matches[0]

    return None


def copy_selected_pdfs(
    csv_path=DEFAULT_CSV_PATH,
    source_pdf_dir=DEFAULT_SOURCE_PDF_DIR,
    destination_pdf_dir=DEFAULT_DESTINATION_PDF_DIR,
    missing_csv_path=DEFAULT_MISSING_CSV_PATH,
):
    """Copy selected PDFs into data/pdfs/<case_year>/ and record missing files."""
    csv_path = Path(csv_path)
    source_pdf_dir = Path(source_pdf_dir)
    destination_pdf_dir = Path(destination_pdf_dir)
    missing_csv_path = Path(missing_csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Selected judgments CSV not found: {csv_path}")

    if not source_pdf_dir.exists():
        raise FileNotFoundError(f"Source PDF folder not found: {source_pdf_dir}")

    ensure_folder(destination_pdf_dir)
    ensure_folder(missing_csv_path.parent)

    df = pd.read_csv(csv_path)
    required_columns = {"temp_link", "case_year", "diary_no", "case_no"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        raise ValueError(f"CSV missing required columns: {sorted(missing_columns)}")

    copied_count = 0
    already_exists_count = 0
    missing_rows = []

    print(f"Reading selected judgments from: {csv_path}")
    print(f"Source PDF folder: {source_pdf_dir}")
    print(f"Destination PDF folder: {destination_pdf_dir}")

    for _, row in df.iterrows():
        temp_link = row.get("temp_link")
        pdf_filename = get_pdf_filename(temp_link)
        case_year = row.get("case_year")

        if not pdf_filename or pd.isna(case_year):
            missing_rows.append(
                {
                    "pdf_filename": pdf_filename,
                    "temp_link": temp_link,
                    "case_year": case_year,
                    "diary_no": row.get("diary_no"),
                    "case_no": row.get("case_no"),
                    "reason": "missing filename or case_year",
                }
            )
            continue

        source_pdf = find_source_pdf(
            source_pdf_dir,
            pdf_filename,
            temp_link,
            diary_no=row.get("diary_no"),
        )
        if source_pdf is None:
            missing_rows.append(
                {
                    "pdf_filename": pdf_filename,
                    "temp_link": temp_link,
                    "case_year": case_year,
                    "diary_no": row.get("diary_no"),
                    "case_no": row.get("case_no"),
                    "reason": "source PDF not found",
                }
            )
            continue

        year_folder = ensure_folder(destination_pdf_dir / str(int(case_year)))
        destination_pdf = year_folder / pdf_filename

        if destination_pdf.exists():
            already_exists_count += 1
            continue

        shutil.copy2(source_pdf, destination_pdf)
        copied_count += 1

    missing_df = pd.DataFrame(
        missing_rows,
        columns=[
            "pdf_filename",
            "temp_link",
            "case_year",
            "diary_no",
            "case_no",
            "reason",
        ],
    )
    missing_df.to_csv(missing_csv_path, index=False)

    summary = {
        "total_rows": len(df),
        "copied": copied_count,
        "already_existing": already_exists_count,
        "missing": len(missing_rows),
        "missing_csv_path": str(missing_csv_path),
    }

    print("\nPDF organization summary")
    print(f"Total rows in CSV: {summary['total_rows']}")
    print(f"PDFs copied: {summary['copied']}")
    print(f"PDFs already existing: {summary['already_existing']}")
    print(f"PDFs missing: {summary['missing']}")
    print(f"Missing details saved to: {missing_csv_path}")

    if missing_rows:
        print("\nMissing PDF filenames:")
        for missing in missing_rows:
            print(f"- {missing['pdf_filename']}")

    return summary


def main():
    """Run the selected PDF organizer."""
    copy_selected_pdfs()


if __name__ == "__main__":
    main()
