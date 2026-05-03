import os
import re

import pandas as pd


CSV_PATH = "judgments.csv"
OUTPUT_PATH = "judgement_case_year_complete.csv"
MVP_OUTPUT_PATH = "judgement_mvp_dataset.csv"

CASE_PATTERN = "Crl.A."
YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")
VERNACULAR_PATTERN = re.compile(r"vernacular", re.IGNORECASE)
RANDOM_STATE = 42
MVP_MIN_CASE_YEAR = 2008
MVP_MAX_CASE_YEAR = 2023
MVP_MAX_CASES_PER_YEAR = 15


def extract_case_year(case_no):
    """Extract a 1900-2099 year from case_no; return missing for invalid input."""
    if pd.isna(case_no):
        return pd.NA

    match = YEAR_PATTERN.search(str(case_no))
    if match is None:
        return pd.NA

    return int(match.group(1))


def load_dataset(csv_path=CSV_PATH):
    """Load the source Supreme Court judgments CSV."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    print(f"Loading dataset from {csv_path}")
    return pd.read_csv(csv_path)


def add_case_year(df):
    """Add case_year parsed from case_no while preserving the original data."""
    curated = df.copy()
    curated["case_year"] = curated["case_no"].apply(extract_case_year)
    return curated


def filter_criminal_appeals(df):
    """Keep only Criminal Appeal cases where case_no contains Crl.A."""
    case_no = df["case_no"].astype("string")
    mask = case_no.str.contains(re.escape(CASE_PATTERN), case=False, na=False)
    return df[mask].copy()


def filter_missing_case_year(df):
    """Remove rows where a valid case year could not be extracted."""
    case_year = pd.to_numeric(df["case_year"], errors="coerce")
    filtered = df[case_year.notna()].copy()
    filtered["case_year"] = case_year[case_year.notna()].astype(int)
    return filtered


def filter_english_quality_rows(df):
    """Keep English-quality rows: missing language and no vernacular PDF path."""
    temp_link = df["temp_link"].astype("string")
    missing_language_mask = df["language"].isna()
    non_vernacular_mask = ~temp_link.str.contains(VERNACULAR_PATTERN, na=False)

    return df[missing_language_mask & non_vernacular_mask].copy()


def remove_low_quality_entries(df):
    """Drop rows without usable PDF links and remove duplicate case numbers."""
    cleaned = df.dropna(subset=["temp_link"]).copy()
    cleaned = cleaned[cleaned["temp_link"].astype("string").str.strip().ne("")]
    cleaned = cleaned.drop_duplicates(subset=["case_no"], keep="first")
    return cleaned.reset_index(drop=True)


def build_curated_dataset(df):
    """Run the complete Legal Vakta criminal-appeal dataset curation pipeline."""
    print("Extracting case_year from case_no")
    curated = add_case_year(df)

    print("Filtering Criminal Appeal cases")
    curated = filter_criminal_appeals(curated)

    print("Removing rows without valid case_year")
    curated = filter_missing_case_year(curated)

    print("Applying English-quality language and PDF path filters")
    curated = filter_english_quality_rows(curated)

    print("Removing missing links and duplicate case numbers")
    curated = remove_low_quality_entries(curated)

    return curated.sort_values(["case_year", "case_no"]).reset_index(drop=True)


def preview_random_cases(df, count=5, random_state=RANDOM_STATE):
    """Return up to count random selected cases for quick manual inspection."""
    if df.empty:
        return df.copy()

    sample_size = min(count, len(df))
    return df.sample(n=sample_size, random_state=random_state).reset_index(drop=True)


def build_balanced_mvp_dataset(
    df,
    min_year=MVP_MIN_CASE_YEAR,
    max_year=MVP_MAX_CASE_YEAR,
    max_cases_per_year=MVP_MAX_CASES_PER_YEAR,
    random_state=RANDOM_STATE,
):
    """Create the final balanced MVP dataset: 2008-2023, up to 15 cases per year."""
    df_final = df[(df["case_year"] >= min_year) & (df["case_year"] <= max_year)].copy()

    if df_final.empty:
        return df_final

    sampled_groups = [
        group.sample(min(len(group), max_cases_per_year), random_state=random_state)
        for _, group in df_final.groupby("case_year", sort=True)
    ]
    final_balanced = pd.concat(sampled_groups, ignore_index=True)

    return (
        final_balanced.sort_values(["case_year", "case_no"])
        .reset_index(drop=True)
    )


def print_summary(df):
    """Print high-level dataset quality and coverage summary."""
    print("\nDataset summary")
    print(f"Total selected cases: {len(df)}")

    if df.empty:
        print("Cases per year: no cases selected")
        print("Year range covered: unavailable")
        return

    cases_per_year = df.groupby("case_year").size().sort_index()

    print("Cases per year:")
    for year, count in cases_per_year.items():
        print(f"{year}: {count}")

    print(f"Year range covered: {int(df['case_year'].min())} - {int(df['case_year'].max())}")


def print_preview(df, count=5):
    """Print a compact preview of random curated cases."""
    preview_columns = [
        column
        for column in ["case_no", "case_year", "pet", "res", "judgment_dates", "temp_link"]
        if column in df.columns
    ]

    print(f"\nRandom preview ({min(count, len(df))} cases):")
    if df.empty:
        print("No cases available for preview.")
        return

    preview = preview_random_cases(df, count=count)
    print(preview[preview_columns].to_string(index=False))


def save_dataset(df, output_path=OUTPUT_PATH):
    """Save the curated dataset as CSV."""
    df.to_csv(output_path, index=False)
    print(f"\nSaved curated dataset to {output_path}")


def main():
    df = load_dataset(CSV_PATH)
    curated_df = build_curated_dataset(df)
    save_dataset(curated_df, OUTPUT_PATH)
    print_summary(curated_df)
    print_preview(curated_df)

    print("\nCreating balanced MVP dataset for case years 2008-2023")
    final_balanced = build_balanced_mvp_dataset(curated_df)
    save_dataset(final_balanced, MVP_OUTPUT_PATH)
    print_summary(final_balanced)


if __name__ == "__main__":
    main()
