import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCANS_DIR = PROJECT_ROOT / "scans"
OUTPUT_DIR = PROJECT_ROOT / "output"
JSON_DIR = OUTPUT_DIR / "json"

IMAGE_DPI = 200
MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 5
