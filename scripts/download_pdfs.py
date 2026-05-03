"""Organize existing local PDFs into data/pdfs.

This project already has PDFs locally. This script copies from a source folder
into data/pdfs. If filenames are already arranged in year folders, that layout
is preserved.
"""

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import Settings


def copy_existing_pdfs(source_dir: Path, destination_dir: Path):
    """Copy PDFs from source_dir to destination_dir preserving relative paths."""
    if not source_dir.exists():
        raise FileNotFoundError(f"Source PDF directory not found: {source_dir}")

    destination_dir.mkdir(parents=True, exist_ok=True)
    pdf_paths = sorted(source_dir.glob("**/*.pdf"))
    copied = 0

    for pdf_path in pdf_paths:
        relative_path = pdf_path.relative_to(source_dir)
        target_path = destination_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists():
            continue
        shutil.copy2(pdf_path, target_path)
        copied += 1

    return copied, len(pdf_paths)


def main():
    """Copy top-level ./pdfs into ./data/pdfs."""
    source_dir = PROJECT_ROOT / "pdfs"
    copied, total = copy_existing_pdfs(source_dir, Settings.pdf_dir)
    print(f"Copied {copied} of {total} PDFs into {Settings.pdf_dir}")


if __name__ == "__main__":
    main()
