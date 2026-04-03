"""
Per-item extraction via segmented image crops + VLM.

For every checkbox item and every Likert-table row, a separate VLM call
decides the answer for that single item. This eliminates cross-item
confusion and improves answer-change detection.
"""

import base64
import json
from pathlib import Path

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import OPENAI_API_KEY, OPENAI_MODEL, MAX_RETRIES, RETRY_WAIT_SECONDS
from .schema import (
    Q4_OPTIONS, Q5_SCALE, Q5_ITEMS, Q6_SCALE, Q6_ITEMS,
    Q7_OPTIONS, Q8_OPTIONS, Q9_OPTIONS, Q10_OPTIONS, Q11_OPTIONS,
    Q12_SCALE, Q12_ITEMS, Q13_OPTIONS, Q14_OPTIONS, Q15_OPTIONS,
    Q16_OPTIONS, Q17_OPTIONS, Q18_SCALE, Q18_ITEMS,
    Q19_OPTIONS, Q20_SCALE, Q20_ITEMS,
)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def _encode_image(path: Path) -> str:
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def _img_block(path: Path) -> dict:
    return {"type": "image_url",
            "image_url": {"url": _encode_image(path), "detail": "high"}}


ANSWER_CHANGE_NOTICE = (
    "CRITICAL — The respondent may have crossed out an earlier mark and "
    "chosen a different option.  A crossed-out mark looks like a heavy "
    "scribble, an X through a circle, or a line through the mark.  "
    "If you see MULTIPLE marks, identify the FINAL intended answer "
    "(the one NOT crossed out) and note the change."
)

SYSTEM_PROMPT = (
    "You are an expert data-entry assistant reading ONE specific item "
    "from a scanned hand-filled paper survey.  Focus ONLY on the item "
    "described in the user prompt.  Return valid JSON matching the "
    "schema provided."
)


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=RETRY_WAIT_SECONDS, min=2, max=60),
    reraise=True,
)
def _call_api(prompt: str, schema: dict, images: list[dict]) -> dict:
    client = _get_client()
    user_content: list[dict] = [{"type": "text", "text": prompt}]
    user_content.extend(images)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "item_answer",
                "strict": True,
                "schema": schema,
            },
        },
        temperature=0.0,
        max_completion_tokens=512,
    )
    return json.loads(response.choices[0].message.content)


_BOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "checked": {"type": "boolean"},
        "notes": {"type": "string"},
    },
    "required": ["checked", "notes"],
    "additionalProperties": False,
}

_RATING_SCHEMA = {
    "type": "object",
    "properties": {
        "rating": {"type": ["integer", "null"], "enum": [1, 2, 3, 4, 5, None]},
        "notes": {"type": "string"},
    },
    "required": ["rating", "notes"],
    "additionalProperties": False,
}


def _nullable_enum_schema(options: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "value": {"type": ["string", "null"], "enum": [*options, None]},
            "notes": {"type": "string"},
        },
        "required": ["value", "notes"],
        "additionalProperties": False,
    }


# ── Mapping tables ──────────────────────────────────────────────────────

TABLE_META: dict[str, tuple[str, str, list[str], list[tuple[str, str]]]] = {
    "q5":  ("Q5", "Satisfaction with communication",  Q5_SCALE,  Q5_ITEMS),
    "q6":  ("Q6", "Agreement about supervisor",       Q6_SCALE,  Q6_ITEMS),
    "q12": ("Q12", "Preferred communication channels", Q12_SCALE, Q12_ITEMS),
    "q18": ("Q18", "Preferred feedback methods",       Q18_SCALE, Q18_ITEMS),
    "q20": ("Q20", "Usefulness of improvements",       Q20_SCALE, Q20_ITEMS),
}

MULTI_META: dict[str, tuple[str, str, list[str]]] = {
    "q9":  ("Q9",  "Types of info received timely",       Q9_OPTIONS),
    "q10": ("Q10", "Types most interested in receiving",   Q10_OPTIONS),
    "q11": ("Q11", "Usual information sources",            Q11_OPTIONS),
}

SINGLE_META: dict[str, tuple[str, str, list[str]]] = {
    "q4_years_at_sha":   ("Q4",  "How many years worked for SHA?",        Q4_OPTIONS),
    "q7_timely_info":    ("Q7",  "How often receive info early enough?",   Q7_OPTIONS),
    "q8_miss_info":      ("Q8",  "How often miss relevant info?",          Q8_OPTIONS),
    "q13_email_freq":    ("Q13", "How often check SHA email?",             Q13_OPTIONS),
    "q14_awareness":     ("Q14", "Aware of whom to go to for help?",       Q14_OPTIONS),
    "q15_comfort":       ("Q15", "Comfortable speaking up?",               Q15_OPTIONS),
    "q16_feedback_ease": ("Q16", "How easy to give feedback?",             Q16_OPTIONS),
    "q17_feedback_action": ("Q17", "Feedback leads to action?",            Q17_OPTIONS),
    "q19_feel_important":  ("Q19", "Communication makes you feel important?", Q19_OPTIONS),
}


# ── Per-type extractors ─────────────────────────────────────────────────

def _extract_text(seg: dict, notes: list[str], verbose: bool) -> dict:
    questions = seg["questions"]
    images = [_img_block(seg["crop_path"])]

    if "q21_comments" in questions:
        prompt = (
            "This image shows Q21 of the MDOT SHA employee survey.\n"
            "Transcribe the handwritten response as accurately as possible.\n\n"
            "IMPORTANT CONTEXT:\n"
            "- 'SHA' stands for State Highway Administration (MDOT SHA)\n"
            "- Common abbreviations: SHA, MDOT, FMT, HQ\n"
            "- If you see 'SHA' in the handwriting, keep it as 'SHA'\n"
            "- Read each word carefully character by character\n"
            "- Preserve the respondent's exact wording and spelling\n"
            "Return null if the field is blank."
        )
        schema = {
            "type": "object",
            "properties": {
                "q21_comments": {"type": ["string", "null"]},
                "notes": {"type": "string"},
            },
            "required": ["q21_comments", "notes"],
            "additionalProperties": False,
        }
        if verbose:
            print(f"    q21 (text)")
        r = _call_api(prompt, schema, images)
        n = r.pop("notes", "")
        if n and n.lower() not in ("", "none", "all clear"):
            notes.append(f"q21: {n}")
        return r
    else:
        prompt = (
            "This image shows Q1-Q3 of an MDOT SHA employee survey.\n"
            "Q1: Current role/job at MDOT SHA (handwritten text)\n"
            "Q2: District (number or name)\n"
            "Q3: Shop (location name)\n\n"
            "Common job titles: FMT (Field Maintenance Technician), "
            "Crew Leader, Equipment Operator, TEII, etc.\n"
            "Transcribe each field exactly. Return null if blank."
        )
        schema = {
            "type": "object",
            "properties": {
                "q1_role": {"type": ["string", "null"]},
                "q2_district": {"type": ["string", "null"]},
                "q3_shop": {"type": ["string", "null"]},
                "notes": {"type": "string"},
            },
            "required": ["q1_role", "q2_district", "q3_shop", "notes"],
            "additionalProperties": False,
        }
        if verbose:
            print(f"    q1-q3 (text)")
        r = _call_api(prompt, schema, images)
        n = r.pop("notes", "")
        if n and n.lower() not in ("", "none", "all clear"):
            notes.append(f"q1_q3: {n}")
        return r


def _extract_single_choice(seg: dict, notes: list[str], verbose: bool) -> dict:
    field = seg["questions"][0]
    qnum, desc, options = SINGLE_META[field]
    opts = " | ".join(options)
    images = [_img_block(seg["crop_path"])]
    prompt = (
        f"This image shows {qnum}: {desc}\n"
        f"Options: {opts}\n\n"
        f"{ANSWER_CHANGE_NOTICE}\n"
        f"Which option is marked? Return the exact text. null if none."
    )
    schema = _nullable_enum_schema(options)
    if verbose:
        print(f"    {field}")
    r = _call_api(prompt, schema, images)
    n = r.pop("notes", "")
    if n and n.lower() not in ("", "none", "all clear"):
        notes.append(f"{field}: {n}")
    return {field: r["value"]}


def _extract_multi_select(seg: dict, notes: list[str], verbose: bool) -> dict:
    """One VLM call per checkbox item → True/False."""
    sel_field = seg["questions"][0]
    other_field = seg["questions"][1] if len(seg["questions"]) > 1 else None
    qnum, desc, options = MULTI_META[seg["id"]]
    images = [_img_block(seg["crop_path"])]

    selected: list[str] = []
    for opt in options:
        prompt = (
            f"This image shows {qnum}: \"{desc}\" (select all that apply).\n"
            f"Focus on the item: \"{opt}\"\n\n"
            f"Is the checkbox next to \"{opt}\" CHECKED?\n"
            f"A checked box has a mark through or inside it "
            f"(✓, X, filled, scribble). An unchecked box is empty (□).\n\n"
            f"{ANSWER_CHANGE_NOTICE}\n"
            f"Return {{\"checked\": true/false, \"notes\": \"...\"}}"
        )
        if verbose:
            print(f"    {sel_field} > {opt[:40]}")
        r = _call_api(prompt, _BOOL_SCHEMA, images)
        n = r.get("notes", "")
        if n and n.lower() not in ("", "none", "all clear", "no change"):
            notes.append(f"{sel_field}[{opt}]: {n}")
        if r["checked"]:
            selected.append(opt)

    result: dict = {sel_field: selected}

    if other_field:
        prompt_other = (
            f"This image shows {qnum}. Is there handwritten text in the "
            f"\"Other:\" line? Transcribe it. Return null if blank."
        )
        schema_other = {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "null"]},
                "notes": {"type": "string"},
            },
            "required": ["value", "notes"],
            "additionalProperties": False,
        }
        if verbose:
            print(f"    {other_field}")
        r = _call_api(prompt_other, schema_other, images)
        result[other_field] = r["value"]

    return result


def _extract_likert_table(seg: dict, notes: list[str], verbose: bool) -> dict:
    """One VLM call per table row with header crop for column alignment."""
    base_id = seg["id"].split("_")[0] if "_" in seg["id"] else seg["id"]
    if base_id not in TABLE_META:
        base_id = seg["id"]
    qnum, desc, scale, items = TABLE_META[base_id]
    n_cols = len(scale)
    scale_str = " | ".join(f"Col {i+1}={s}" for i, s in enumerate(scale))

    row_crops = seg.get("row_crops", [])
    header_path = seg.get("header_crop_path")
    result: dict = {}

    for ri, (col, label) in enumerate(items):
        if col not in seg["questions"]:
            continue

        images: list[dict] = []
        if header_path:
            images.append(_img_block(header_path))
        if ri < len(row_crops):
            images.append(_img_block(row_crops[ri]["row_crop_path"]))
        images.append(_img_block(seg["crop_path"]))

        prompt = (
            f"You are reading ONE row of the {qnum} table: \"{desc}\".\n"
            f"The table has {n_cols} rating columns from left to right:\n"
            f"  {scale_str}\n\n"
            f"I am sending you up to 3 images:\n"
            f"  1. The TABLE HEADER row (column labels) - use this to "
            f"align column positions precisely.\n"
            f"  2. The SPECIFIC ROW crop for \"{label}\".\n"
            f"  3. The FULL TABLE crop for overall context.\n\n"
            f"TASK: In the row for \"{label}\", which column contains "
            f"the respondent's handwritten mark?\n"
            f"A mark can be a check, X, circle fill, heavy scribble, "
            f"or any handwriting inside a cell. An EMPTY cell has only "
            f"a small pre-printed circle (o) with no handwriting.\n\n"
            f"COUNTING: Carefully match the mark's horizontal position "
            f"against the column headers. Count columns starting from "
            f"1 on the left. Do NOT guess - verify by checking that the "
            f"mark lines up with the correct header column.\n\n"
            f"{ANSWER_CHANGE_NOTICE}\n\n"
            f"Return {{\"rating\": <1-{n_cols} or null>, \"notes\": \"...\"}}"
        )
        if verbose:
            print(f"    {col}")
        r = _call_api(prompt, _RATING_SCHEMA, images)
        n = r.get("notes", "")
        if n and n.lower() not in ("", "none", "all clear", "no change"):
            notes.append(f"{col}: {n}")
        result[col] = r["rating"]

    if seg["id"] == "q18":
        images = [_img_block(seg["crop_path"])]
        prompt_other = (
            f"This image shows the Q18 table. Look at the LAST row "
            f"labeled \"Other:\". Is there handwritten text in that row? "
            f"Transcribe it. Also identify which column (1-5) has the "
            f"rating mark, or null if no mark.\n\n"
            f"Columns: {scale_str}\n"
            f"Return {{\"text\": \"...\", \"rating\": <1-5 or null>, \"notes\": \"...\"}}"
        )
        schema_other = {
            "type": "object",
            "properties": {
                "text": {"type": ["string", "null"]},
                "rating": {"type": ["integer", "null"], "enum": [1, 2, 3, 4, 5, None]},
                "notes": {"type": "string"},
            },
            "required": ["text", "rating", "notes"],
            "additionalProperties": False,
        }
        if verbose:
            print(f"    q18_other")
        r = _call_api(prompt_other, schema_other, images)
        result["q18_other_text"] = r["text"]
        result["q18_other_rating"] = r["rating"]

    return result


# ── Main orchestrator ───────────────────────────────────────────────────

def extract_segments(segments: list[dict], verbose: bool = True) -> dict:
    """
    Extract answers from segmented question crops, one item at a time.

    Returns a merged dict matching the full survey JSON schema.
    """
    merged: dict = {}
    all_notes: list[str] = []

    for seg in segments:
        if seg.get("continuation"):
            continue

        qtype = seg["qtype"]
        if verbose:
            print(f"  [{seg['id']}]")

        handler = {
            "text": _extract_text,
            "single_choice": _extract_single_choice,
            "multi_select": _extract_multi_select,
            "likert_table": _extract_likert_table,
        }[qtype]

        result = handler(seg, all_notes, verbose)
        merged.update(result)

    cont_segs = [s for s in segments if s["id"] == "q19_cont"]
    if cont_segs:
        if verbose:
            print(f"  [q19_cont]")
            print(f"    q19_feel_important (continuation)")
        images = [_img_block(cont_segs[0]["crop_path"])]
        prompt = (
            "This image shows the CONTINUATION of Q19.\n"
            "Q19: To what extent does communication at SHA make you feel "
            "like being an important part of it?\n"
            "Remaining options on this page: Somewhat | Mostly | Very much\n\n"
            f"{ANSWER_CHANGE_NOTICE}\n"
            "Return the selected option, or null if no mark on this page."
        )
        schema = _nullable_enum_schema(Q19_OPTIONS)
        r = _call_api(prompt, schema, images)
        n = r.pop("notes", "")
        if n and n.lower() not in ("", "none", "all clear"):
            all_notes.append(f"q19_cont: {n}")
        if r.get("value"):
            merged["q19_feel_important"] = r["value"]

    merged["_confidence_notes"] = (
        "; ".join(all_notes) if all_notes else "All answers clear."
    )
    return merged
