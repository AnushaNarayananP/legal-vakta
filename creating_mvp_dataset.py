CSV_PATH = r"C:\Users\HP\RAG_AI\Rag_Project_Legal_Vakta\judgments.csv"
PDF_ROOT = r"C:\Users\HP\RAG_AI\Rag_Project_Legal_Vakta\pdfs"
OUTPUT_DIR = r"C:\Users\HP\RAG_AI\Rag_Project_Legal_Vakta\Legal_Vakta_Data"

import os
import shutil
import pandas as pd
from pathlib import Path


# Phase 1: 200 PDFs split
TARGET_COUNTS = {
    "criminal": 70,
    "civil": 70,
    "constitutional": 30,
    "other": 30
}

# CSV columns to keep for Phase 1
METADATA_COLUMNS = [
    "case_no",
    "pet",
    "res",
    "bench",
    "judgement_by",
    "judgment_dates",
    "temp_link"
]

def categorize_case(case_no):
    case_no = str(case_no).lower()

    if "crl" in case_no or "criminal" in case_no:
        return "criminal"
    elif "c.a." in case_no or "civil" in case_no:
        return "civil"
    elif "w.p" in case_no or "writ" in case_no:
        return "constitutional"
    else:
        return "other"

def find_pdf(pdf_root, temp_link):
    """
    temp_link example:
    supremecourt/2021/5/5_2021_36_1501_28814_Judgement_23-Jul-2021.pdf
    
    Now searches by matching key parts from temp_link to actual PDF filenames.
    """
    temp_link = str(temp_link).replace("\\", "/")
    
    # Extract useful parts from temp_link for matching
    # e.g., from "5_2021_36_1501_28814_Judgement_23-Jul-2021.pdf" 
    # extract "5_2021" or "28814" or "Judgement_23-Jul-2021"
    filename = os.path.basename(temp_link)
    name_without_ext = os.path.splitext(filename)[0]
    
    # Try different matching strategies
    # Strategy 1: Look for files containing the diary_no or case year
    parts = name_without_ext.split("_")
    search_terms = []
    if len(parts) >= 2:
        # First part is usually diary number like "5_2021"
        search_terms.append(parts[0])
        search_terms.append(parts[1])
    # Add the full name without extension
    search_terms.append(name_without_ext)
    
    # Walk through PDF root and find matching files
    for root, dirs, files in os.walk(pdf_root):
        for f in files:
            if f.endswith('.pdf'):
                f_base = os.path.splitext(f)[0]
                # Check if any search term matches
                for term in search_terms:
                    if term and term in f_base:
                        return os.path.join(root, f)
    
    # Last resort: try exact filename match
    for root, dirs, files in os.walk(pdf_root):
        if filename in files:
            return os.path.join(root, filename)

    return None

def main():
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create Phase 1 folder structure
    (output_path / "01_selected_200_pdfs").mkdir(parents=True, exist_ok=True)
    for category in TARGET_COUNTS:
        (output_path / "01_selected_200_pdfs" / category).mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(CSV_PATH)

    needed_columns = [
        "diary_no",
        "Judgement_type",
        "case_no",
        "pet",
        "res",
        "bench",
        "judgement_by",
        "judgment_dates",
        "temp_link"
    ]

    df = df[METADATA_COLUMNS].copy()
    df = df.dropna(subset=["case_no", "temp_link"])

    df["category"] = df["case_no"].apply(categorize_case)

    selected_rows = []
    copied_count = {"criminal": 0, "civil": 0, "constitutional": 0, "other": 0}
    missing_pdfs = []

    for category, count in TARGET_COUNTS.items():
        category_df = df[df["category"] == category].copy()

        category_df = category_df.drop_duplicates(subset=["temp_link"])

        selected = category_df.head(count)

        print(f"{category}: selected {len(selected)} rows from CSV")

        for _, row in selected.iterrows():
            source_pdf = find_pdf(PDF_ROOT, row["temp_link"])

            if source_pdf is None:
                missing_pdfs.append(row["temp_link"])
                continue

            filename = os.path.basename(source_pdf)
            destination_pdf = output_path / "01_selected_200_pdfs" / category / filename

            shutil.copy2(source_pdf, destination_pdf)

            row_dict = row.to_dict()
            row_dict["local_pdf_path"] = str(destination_pdf)
            row_dict["category"] = category
            selected_rows.append(row_dict)
            copied_count[category] += 1

    # Only keep rows where PDF was actually copied
    selected_df = pd.DataFrame(selected_rows)
    selected_df = selected_df[selected_df["local_pdf_path"].notna()].copy()
    
    selected_csv_path = output_path / "02_metadata" / "selected_judgments.csv"
    selected_csv_path.parent.mkdir(parents=True, exist_ok=True)
    selected_df.to_csv(selected_csv_path, index=False)

    # Create placeholder for vectorstore
    (output_path / "03_vectorstore").mkdir(parents=True, exist_ok=True)

    print("\n" + "="*50)
    print("Phase 1 Dataset Created!")
    print("="*50)
    print(f"\nFolder structure:")
    print(f"  {OUTPUT_DIR}/")
    print(f"  ├── 01_selected_200_pdfs/")
    print(f"  │   ├── criminal/ ({copied_count['criminal']})")
    print(f"  │   ├── civil/ ({copied_count['civil']})")
    print(f"  │   ├── constitutional/ ({copied_count['constitutional']})")
    print(f"  │   └── other/ ({copied_count['other']})")
    print(f"  ├── 02_metadata/")
    print(f"  │   └── selected_judgments.csv")
    print(f"  └── 03_vectorstore/")
    
    total_copied = sum(copied_count.values())
    total_missing = len(missing_pdfs)
    print(f"\n📊 ACTUAL RESULTS:")
    print(f"  ✓ PDFs successfully copied: {total_copied}")
    print(f"  ✗ PDFs not found: {total_missing}")
    
    if missing_pdfs:
        print(f"\n⚠️  First 10 missing PDFs:")
        for mp in missing_pdfs[:10]:
            print(f"     - {mp}")

if __name__ == "__main__":
    main()