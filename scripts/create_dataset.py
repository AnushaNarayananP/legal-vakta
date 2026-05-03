"""Create the processed Legal Vakta metadata CSV."""

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset_descreibe import CSV_PATH, MVP_OUTPUT_PATH, build_balanced_mvp_dataset, build_curated_dataset
from src.config import Settings

import pandas as pd


def main():
    """Build selected_judgments.csv from judgments.csv."""
    Settings.raw_dir.mkdir(parents=True, exist_ok=True)
    Settings.processed_dir.mkdir(parents=True, exist_ok=True)

    source_csv = PROJECT_ROOT / CSV_PATH
    if not source_csv.exists():
        raise FileNotFoundError(f"Missing source CSV: {source_csv}")

    shutil.copy2(source_csv, Settings.raw_csv_path)
    df = pd.read_csv(source_csv)
    curated = build_curated_dataset(df)
    selected = build_balanced_mvp_dataset(curated)

    selected.to_csv(Settings.selected_csv_path, index=False)
    selected.to_csv(PROJECT_ROOT / MVP_OUTPUT_PATH, index=False)

    print(f"Saved raw CSV to {Settings.raw_csv_path}")
    print(f"Saved selected metadata to {Settings.selected_csv_path}")
    print(f"Selected rows: {len(selected)}")
    print(selected.groupby("case_year").size().sort_index().to_string())


if __name__ == "__main__":
    main()
