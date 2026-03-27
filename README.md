# SHA Field Employee Survey — scanned PDF extraction

Turn hand-filled survey PDFs into structured JSON, then aggregate to CSV and Excel using OpenAI vision (default: `gpt-4o`).

## Prerequisites

- **Python 3.10+**
- **Poppler** on your PATH (provides `pdftoppm`, used by `pdf2image`). On Windows, MiKTeX or a standalone Poppler build works.
- An **OpenAI API key** with access to the chosen vision model.

## Setup

```bash
cd side_proj_OCR
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
# optional:
# OPENAI_MODEL=gpt-4o-mini
```

Put scanned questionnaires as PDFs in the `scans/` folder (one completed survey per PDF; typically six pages).

## Usage

Run from the project root (`side_proj_OCR`).

| Command | What it does |
|--------|----------------|
| `python -m src.main` | Process every `*.pdf` in `scans/` |
| `python -m src.main --input-dir path/to/pdfs` | Use another input folder |
| `python -m src.main --single-file scans/scan0011.pdf` | Process one file |
| `python -m src.main --aggregate-only` | Skip API calls; rebuild CSV/Excel from existing `output/json/*.json` |
| `python -m src.main --force-reprocess` | Re-run extraction even if a JSON file already exists |

**Checkpointing:** If `output/json/<stem>.json` already exists for a PDF, that file is skipped unless you pass `--force-reprocess`.

**Image cache:** Converted page PNGs are stored under `scans/.image_cache/` so repeat runs do not re-rasterize PDFs.

## Outputs

| Path | Description |
|------|-------------|
| `output/json/<name>.json` | One structured response per survey PDF |
| `output/survey_results.csv` | All rows combined (includes expanded checkbox columns) |
| `output/survey_results.xlsx` | Same data in Excel |
| `output/qa_review.csv` | Rows flagged for review (e.g. model uncertainty notes, empty extractions) |

Question definitions and allowed values live in `src/schema.py`.

## Project layout

```
scans/              # input PDFs (gitignored by default)
output/json/        # per-respondent JSON
output/             # CSV, Excel, QA report
src/
  main.py           # CLI entry point
  schema.py         # survey schema + prompts
  pdf_to_images.py  # PDF → PNG
  extractor.py      # OpenAI vision call
  aggregator.py     # JSON → CSV/Excel
  qa_report.py      # QA flags
```

Do not commit `.env` or real survey data; keep API keys and outputs private per your IRB and data policy.
