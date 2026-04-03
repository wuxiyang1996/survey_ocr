"""
CLI orchestrator — batch-process scanned survey PDFs.

Usage:
    python -m src.main                          # process all PDFs in scans/
    python -m src.main --input-dir scans/
    python -m src.main --single-file scans/scan0011.pdf
    python -m src.main --aggregate-only         # skip extraction, just rebuild CSV/Excel
    python -m src.main --force-reprocess        # ignore cached JSON, re-extract everything
"""

import argparse
import json
import sys
from pathlib import Path

from tqdm import tqdm

from .config import SCANS_DIR, OUTPUT_DIR, JSON_DIR, OPENAI_API_KEY
from .pdf_to_images import pdf_to_images
from .extractor import extract_survey
from .segmenter import segment_pages
from .segment_extractor import extract_segments
from .aggregator import aggregate
from .qa_report import generate_qa_report

SEGMENTS_DIR = OUTPUT_DIR / "segments"


def _process_one(pdf_path: Path, force: bool = False,
                 use_segmented: bool = True) -> bool:
    """
    Process a single scanned PDF.  Returns True on success, False on failure.
    Skips extraction if a JSON output already exists (unless *force*).
    """
    json_out = JSON_DIR / f"{pdf_path.stem}.json"

    if json_out.exists() and not force:
        return True

    try:
        image_paths = pdf_to_images(pdf_path, cache_dir=SCANS_DIR / ".image_cache")
    except Exception as exc:
        print(f"\n  ERROR converting {pdf_path.name} to images: {exc}")
        return False

    try:
        if use_segmented:
            seg_dir = SEGMENTS_DIR / pdf_path.stem
            segments = segment_pages(image_paths, seg_dir)
            result = extract_segments(segments, verbose=True)
        else:
            result = extract_survey(image_paths)
    except Exception as exc:
        print(f"\n  ERROR extracting {pdf_path.name}: {exc}")
        return False

    JSON_DIR.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return True


def run(
    input_dir: Path = SCANS_DIR,
    single_file: Path | None = None,
    output_dir: Path = OUTPUT_DIR,
    force: bool = False,
    aggregate_only: bool = False,
    use_segmented: bool = True,
):
    if not aggregate_only:
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your-api-key-here":
            print("ERROR: Set OPENAI_API_KEY in .env before running extraction.")
            sys.exit(1)

        if single_file:
            pdfs = [single_file]
        else:
            pdfs = sorted(input_dir.glob("*.pdf"))

        if not pdfs:
            print(f"No PDFs found in {input_dir}")
            sys.exit(1)

        print(f"Processing {len(pdfs)} PDF(s) …")
        success = 0
        failed: list[str] = []

        mode = "segmented" if use_segmented else "whole-page"
        print(f"Mode: {mode}")

        for pdf_path in tqdm(pdfs, desc="Extracting", unit="file"):
            ok = _process_one(pdf_path, force=force, use_segmented=use_segmented)
            if ok:
                success += 1
            else:
                failed.append(pdf_path.name)

        print(f"\nExtraction complete: {success} succeeded, {len(failed)} failed.")
        if failed:
            print("Failed files:")
            for name in failed:
                print(f"  - {name}")

    print("\nAggregating results …")
    aggregate(json_dir=JSON_DIR, output_dir=output_dir)

    print("\nGenerating QA report …")
    generate_qa_report(json_dir=JSON_DIR, output_dir=output_dir)

    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(
        description="Extract survey answers from scanned PDF questionnaires."
    )
    parser.add_argument(
        "--input-dir", type=Path, default=SCANS_DIR,
        help="Directory containing scanned PDF files (default: scans/)",
    )
    parser.add_argument(
        "--single-file", type=Path, default=None,
        help="Process a single PDF instead of a whole directory.",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=OUTPUT_DIR,
        help="Output directory (default: output/)",
    )
    parser.add_argument(
        "--force-reprocess", action="store_true",
        help="Re-extract even if JSON output already exists.",
    )
    parser.add_argument(
        "--aggregate-only", action="store_true",
        help="Skip extraction; just rebuild CSV/Excel from existing JSONs.",
    )
    parser.add_argument(
        "--no-segment", action="store_true",
        help="Use the old whole-page extraction instead of per-question segmentation.",
    )

    args = parser.parse_args()
    run(
        input_dir=args.input_dir,
        single_file=args.single_file,
        output_dir=args.output_dir,
        force=args.force_reprocess,
        aggregate_only=args.aggregate_only,
        use_segmented=not args.no_segment,
    )


if __name__ == "__main__":
    main()
