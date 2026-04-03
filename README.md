# SHA Field Employee Survey — Scanned PDF Extraction

This tool reads hand-filled paper surveys that have been scanned into PDF files. It uses OpenAI's vision AI to recognize handwritten answers and turn them into organized data (CSV and Excel spreadsheets). You scan the papers, drop the PDFs into a folder, run one command, and get a clean spreadsheet out the other side.

---

## Table of Contents

1. [What You Need Before Starting](#what-you-need-before-starting)
2. [Getting an OpenAI API Key](#getting-an-openai-api-key)
3. [Installing the Software](#installing-the-software)
4. [Setting Up Your API Key](#setting-up-your-api-key)
5. [Processing Your PDFs](#processing-your-pdfs)
6. [Understanding the Output Files](#understanding-the-output-files)
7. [Common Scenarios](#common-scenarios)
8. [Troubleshooting](#troubleshooting)
9. [Project Layout](#project-layout)
10. [Important Notes on Privacy](#important-notes-on-privacy)

---

## What You Need Before Starting

Before you can use this tool, make sure you have the following three things set up on your computer:

### 1. Python (version 3.10 or newer)

Python is the programming language this tool is written in.

- **One-line install (optional):**
  - **Windows (winget):** `winget install -e --id Python.Python.3.12`
  - **Mac (Homebrew):** `brew install python`
  - **Linux (Debian/Ubuntu):** `sudo apt install python3 python3-pip python3-venv`
  If you use another OS or package manager, install from <https://www.python.org/downloads/> as below.

- **Check if you already have it:** Open a terminal (Command Prompt or PowerShell on Windows) and type:
  ```
  python --version
  ```
  If you see something like `Python 3.12.x`, you're good. If you get an error, you need to install it.
- **To install:** Go to <https://www.python.org/downloads/> and download the latest version. During installation on Windows, **make sure to check the box that says "Add Python to PATH"**.

### 2. Poppler (a PDF rendering library)

Poppler is a behind-the-scenes tool that converts PDF pages into images so the AI can read them.

- **One-line install (optional):**
  - **Windows (winget):** `winget install -e --id oschwartz10612.Poppler`
  - **Mac (Homebrew):** `brew install poppler`
  - **Linux (Debian/Ubuntu):** `sudo apt install poppler-utils`
  After installing on Windows, **open a new terminal** and confirm with `pdftoppm -h`. If winget is not available, use the manual steps below.

- **On Windows (manual, if you prefer not to use winget):**
  1. Download a pre-built Poppler package from <https://github.com/osber/poppler-windows/releases> (or search for "poppler windows download").
  2. Extract the downloaded zip file to a folder, for example `C:\poppler`.
  3. Add the `bin` folder (e.g. `C:\poppler\Library\bin`) to your system PATH:
     - Search for "Environment Variables" in the Windows Start menu.
     - Under "System variables", find `Path`, click Edit, and add the Poppler `bin` folder.
  4. **Verify:** Open a new terminal and type `pdftoppm -h`. If you see help text, Poppler is installed correctly.

### 3. An OpenAI API Key

This tool uses OpenAI's AI to read the handwriting in your scanned surveys. You will need a paid OpenAI API account. See the next section for how to get one.

---

## Getting an OpenAI API Key

The API key is like a password that lets this tool talk to OpenAI's servers. Here's how to get one:

1. **Create an OpenAI account** (or sign in if you already have one):
   Go to <https://platform.openai.com/signup> and sign up.

2. **Add payment information:**
   Go to <https://platform.openai.com/settings/organization/billing/overview> and add a credit card. The AI calls cost money — roughly $0.01–0.05 per survey page processed, depending on the model.

3. **Create an API key:**
   - Go to <https://platform.openai.com/api-keys>.
   - Click **"Create new secret key"**.
   - Give it a name like "Survey Extraction" and click Create.
   - **Copy the key immediately** — it starts with `sk-` and you won't be able to see it again after closing the dialog. Save it somewhere safe (like a password manager).

4. **Set a spending limit (recommended):**
   Go to <https://platform.openai.com/settings/organization/limits> and set a monthly budget so you don't accidentally overspend.

---

## Installing the Software

1. **Open a terminal** (Command Prompt or PowerShell on Windows).

2. **Navigate to the project folder.** For example, if the project is on your D: drive:
   ```
   cd D:\GRA_2025_civil\side_proj_OCR
   ```

3. **Install the required Python packages:**
   ```
   pip install -r requirements.txt
   ```
   This downloads everything the tool needs. It only needs to be done once (or again if the requirements change).

---

## Setting Up Your API Key

The tool reads your OpenAI API key from a small configuration file called `.env`.

1. In the project's root folder (`side_proj_OCR`), create a new text file named `.env` (note the dot at the beginning — it has no name before the dot).

2. Open the file in any text editor (Notepad works fine) and paste the following, replacing the placeholder with your actual key:

   ```
   OPENAI_API_KEY=sk-paste-your-real-key-here
   ```

3. Save and close the file.

**That's it.** The tool will automatically read this file every time it runs.

> **Optional:** If you want to use a different (cheaper) AI model, you can add a second line:
> ```
> OPENAI_API_KEY=sk-paste-your-real-key-here
> OPENAI_MODEL=gpt-4o-mini
> ```
> The default model is `gpt-5.4`. Using `gpt-4o-mini` is cheaper but may be slightly less accurate on difficult handwriting.

---

## Processing Your PDFs

### Step 1: Put your scanned PDFs in the `scans/` folder

Inside the project folder, there is a folder called `scans/`. Copy all your scanned survey PDFs into this folder. Each PDF should contain one completed survey (typically 3–6 pages).

The folder already contains a few sample files to get you started:

| File | Purpose |
|------|---------|
| `scan0011.pdf`, `scan0016.pdf`, … | Example scanned surveys (filled in by hand) |
| `Survey_final_field employee_FINAL.pdf` | The blank survey template for reference |

> **Note:** The blank template PDF (`Survey_final_field employee_FINAL.pdf`) will also be picked up if left in the folder. If you don't want to process it, move it out of `scans/` or into a subfolder before running the tool.

### Step 2: Run the tool

Open a terminal, navigate to the project folder, and run:

```
cd D:\GRA_2025_civil\side_proj_OCR
python -m src.main
```

That's it! The tool will:
1. Find every PDF in the `scans/` folder.
2. Convert each PDF's pages into images.
3. Send the images to OpenAI's AI, which reads the handwriting and extracts the answers.
4. Save each survey's answers as a JSON file.
5. Combine all the answers into a CSV spreadsheet and an Excel file.
6. Generate a QA report flagging anything that looks suspicious.

You will see a progress bar in the terminal showing how many files have been processed.

### Processing a single file

If you only want to process one specific PDF:

```
python -m src.main --single-file scans/scan0011.pdf
```

Replace `scan0011.pdf` with the name of your file.

### Re-processing a file

The tool is smart about not re-doing work. If it already processed a PDF and saved the results, it will skip that file next time. To force it to re-process everything:

```
python -m src.main --force-reprocess
```

### Rebuilding the spreadsheet without re-calling the AI

If you already extracted all the data and just want to regenerate the CSV/Excel files (for example, after manually editing a JSON file):

```
python -m src.main --aggregate-only
```

This is free — it doesn't make any AI calls.

### Using a different input folder

If your PDFs are somewhere else:

```
python -m src.main --input-dir "C:\Users\YourName\Desktop\my_scans"
```

---

## Understanding the Output Files

After processing, look in the `output/` folder. You will find:

| File | What It Contains |
|------|-----------------|
| `output/json/scan0011.json` | The raw extracted answers for one survey (one file per PDF). Useful for debugging or manual review. |
| `output/survey_results.csv` | **All surveys combined into one spreadsheet.** Each row is one survey. You can open this in Excel, Google Sheets, or any data tool. |
| `output/survey_results.xlsx` | Same data as the CSV, but in native Excel format. |
| `output/qa_review.csv` | A list of items that might need a human to double-check — for example, the AI wasn't sure about a handwritten mark, or a rating value looked unusual. |

### How to use the spreadsheet

- Open `survey_results.xlsx` (or `.csv`) in Excel or Google Sheets.
- Each row is one person's survey.
- The `source_file` column tells you which PDF the data came from.
- Multi-select questions (where people could check more than one box) have extra columns that show `1` (checked) or `0` (not checked) for each option.

### How to use the QA report

- Open `qa_review.csv` in Excel or Google Sheets.
- If it's empty, everything looked clean.
- If there are rows, look at the `flag` column to see what the AI was uncertain about, then go back to the original scanned PDF to verify.

---

## Common Scenarios

### "I received 50 new scanned surveys to process"

1. Copy all 50 PDFs into the `scans/` folder.
2. Run `python -m src.main`.
3. Only the new (unprocessed) files will be sent to the AI. Previously processed files are skipped automatically.
4. Open `output/survey_results.xlsx` to see all results.

### "I found a mistake in one survey's results"

1. Open the JSON file in `output/json/` (e.g. `scan0011.json`) in a text editor.
2. Fix the incorrect value.
3. Run `python -m src.main --aggregate-only` to rebuild the spreadsheet with your correction.

### "The AI got a specific survey wrong and I want it to try again"

1. Delete the JSON file for that survey from `output/json/` (e.g. delete `scan0011.json`).
2. Run `python -m src.main`. It will only re-process that one file since the others still have their JSON files.

### "I want to process PDFs from a USB drive without copying them"

```
python -m src.main --input-dir "E:\scanned_surveys"
```

---

## Troubleshooting

### "ERROR: Set OPENAI_API_KEY in .env before running extraction"

The tool can't find your API key. Make sure:
- The `.env` file is in the project's root folder (the `side_proj_OCR` folder, NOT inside `src/`).
- The file is named exactly `.env` (not `.env.txt` — Windows sometimes adds `.txt` silently).
- There are no extra spaces around the `=` sign in the file.

### "No PDFs found in scans/"

Make sure your PDF files are directly inside the `scans/` folder (not in a subfolder) and that they have a `.pdf` extension.

### "ERROR converting ... to images"

This usually means Poppler is not installed or not on your PATH. See the [Poppler installation instructions](#2-poppler-a-pdf-rendering-library) above. After installing, **open a fresh terminal** for the PATH changes to take effect.

### "openai.AuthenticationError" or "Incorrect API key"

Your API key is invalid or expired. Go to <https://platform.openai.com/api-keys>, create a new key, and update your `.env` file.

### "openai.RateLimitError"

You've hit OpenAI's rate limit. This can happen if you process many PDFs at once. Wait a minute and try again — the tool has built-in retry logic that handles most temporary rate limits automatically.

### "The AI is getting answers wrong"

- Check the `qa_review.csv` for flagged items.
- Make sure your scans are clear and not too dark or too light.
- Scan at 200–300 DPI for best results.
- If handwriting is very messy, even the AI may struggle. You can manually edit the JSON file and re-run `--aggregate-only`.

---

## Project Layout

```
side_proj_OCR/
├── .env                  ← Your API key (you create this)
├── requirements.txt      ← Python package list
├── scans/                ← Put your scanned PDF files here
│   ├── scan0011.pdf      ← Example filled-in surveys
│   ├── Survey_final_…    ← Blank survey template (for reference)
│   └── .image_cache/     ← Auto-generated page images (safe to delete)
├── output/
│   ├── json/             ← One JSON file per survey
│   ├── segments/         ← Auto-generated image crops (safe to delete)
│   ├── survey_results.csv
│   ├── survey_results.xlsx
│   └── qa_review.csv
└── src/
    ├── main.py           ← The main program (entry point)
    ├── config.py         ← Settings (API key, paths, etc.)
    ├── schema.py         ← Survey question definitions
    ├── pdf_to_images.py  ← Converts PDFs to images
    ├── segmenter.py      ← Splits page images into question-level crops
    ├── segment_extractor.py  ← Sends each crop to the AI
    ├── extractor.py      ← Alternative: sends whole pages to the AI
    ├── aggregator.py     ← Combines JSON results into CSV/Excel
    └── qa_report.py      ← Generates the QA review report
```

---

## Important Notes on Privacy

- **Do not share your `.env` file or API key** with anyone. Treat it like a password.
- **Survey data may contain personal information.** Do not commit scanned PDFs or output files to Git or upload them to public locations.
- All data sent to OpenAI for processing is subject to [OpenAI's data usage policies](https://openai.com/policies/). Make sure this is acceptable under your IRB protocol or data policy.
