"""
Generate a QA review report that flags uncertain or suspicious extractions.
"""

import csv
import json
from pathlib import Path

from .config import OUTPUT_DIR, JSON_DIR
from .schema import (
    get_all_columns, Q5_ITEMS, Q6_ITEMS, Q12_ITEMS, Q18_ITEMS, Q20_ITEMS,
)

LIKERT_COLUMNS = {c for c, _ in Q5_ITEMS + Q6_ITEMS + Q12_ITEMS + Q18_ITEMS + Q20_ITEMS}
LIKERT_COLUMNS.add("q18_other_rating")


def _check_row(data: dict, source: str) -> list[dict]:
    """Return a list of flag dicts for one respondent."""
    flags: list[dict] = []

    notes = data.get("_confidence_notes", "")
    if notes and notes.strip().lower() != "all answers clear.":
        flags.append({
            "source_file": source,
            "question": "(model notes)",
            "extracted_value": "",
            "flag": notes,
        })

    all_null = True
    for col in get_all_columns():
        if col in ("source_file", "_confidence_notes"):
            continue
        val = data.get(col)
        if val is not None and val != "" and val != []:
            all_null = False
            break
    if all_null:
        flags.append({
            "source_file": source,
            "question": "(all)",
            "extracted_value": "",
            "flag": "Every answer is blank/null — possible extraction failure",
        })

    for col in LIKERT_COLUMNS:
        val = data.get(col)
        if val is not None and val not in (1, 2, 3, 4, 5):
            flags.append({
                "source_file": source,
                "question": col,
                "extracted_value": str(val),
                "flag": f"Likert value out of range 1-5: {val}",
            })

    return flags


def generate_qa_report(
    json_dir: Path | None = None,
    output_dir: Path | None = None,
):
    """
    Scan all per-respondent JSON files and write a qa_review.csv
    containing every flagged item.
    """
    if json_dir is None:
        json_dir = JSON_DIR
    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(json_dir.glob("*.json"))
    if not json_files:
        print("No JSON files found — nothing to review.")
        return

    all_flags: list[dict] = []
    for jf in json_files:
        data = json.loads(jf.read_text(encoding="utf-8"))
        all_flags.extend(_check_row(data, jf.stem))

    qa_path = output_dir / "qa_review.csv"
    fieldnames = ["source_file", "question", "extracted_value", "flag"]
    with open(qa_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_flags:
            writer.writerow(row)

    print(f"Wrote {qa_path}  ({len(all_flags)} flags from {len(json_files)} files)")
    if not all_flags:
        print("No issues flagged — all extractions look clean.")
