"""
Send scanned page images to GPT-4o vision and extract structured survey answers.
"""

import base64
import json
from pathlib import Path

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import OPENAI_API_KEY, OPENAI_MODEL, MAX_RETRIES, RETRY_WAIT_SECONDS
from .schema import SYSTEM_PROMPT, build_user_prompt, build_json_schema


def _encode_image(path: Path) -> str:
    """Return a base64-encoded data URI for a PNG file."""
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/png;base64,{b64}"


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=RETRY_WAIT_SECONDS, min=2, max=60),
    reraise=True,
)
def extract_survey(image_paths: list[Path]) -> dict:
    """
    Call GPT-4o with the page images and return the parsed JSON response dict.

    Raises on API errors after MAX_RETRIES attempts.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    user_content: list[dict] = [
        {"type": "text", "text": build_user_prompt(len(image_paths))}
    ]
    for img_path in image_paths:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": _encode_image(img_path), "detail": "high"},
        })

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": build_json_schema(),
        },
        temperature=0.0,
        max_completion_tokens=4096,
    )

    raw = response.choices[0].message.content
    return json.loads(raw)
