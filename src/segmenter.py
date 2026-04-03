"""
Segment survey page images into individual question-level crops.

Uses a fixed template layout (the SHA survey is a known form) combined with
OpenCV-based table-row detection for Likert-scale grids.

Handles both 6-page scans (scan page = survey page) and 3-page
single-sided scans by auto-detecting which survey page each scan
page corresponds to via a quick VLM call.
"""

import base64
import json
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
from openai import OpenAI

from .config import IMAGE_DPI, OPENAI_API_KEY, OPENAI_MODEL

# ---------------------------------------------------------------------------
# Template layout: maps 1-based page numbers to question crop regions.
# Coordinates are *fractions* of page height (y_start, y_end) so they
# tolerate small DPI or alignment differences across scans.
# x_start / x_end default to full width (0.0 – 1.0).
# ---------------------------------------------------------------------------

QUESTION_REGIONS: dict[int, list[dict]] = {
    2: [
        {"id": "q1_q3", "y_start": 0.09, "y_end": 0.18,
         "questions": ["q1_role", "q2_district", "q3_shop"],
         "qtype": "text"},
        {"id": "q4", "y_start": 0.15, "y_end": 0.30,
         "questions": ["q4_years_at_sha"],
         "qtype": "single_choice"},
        {"id": "q5", "y_start": 0.22, "y_end": 0.55,
         "questions": ["q5_peers", "q5_supervisor", "q5_shop",
                        "q5_leadership", "q5_overall"],
         "qtype": "likert_table"},
        {"id": "q6", "y_start": 0.40, "y_end": 0.73,
         "questions": ["q6_available", "q6_knows_problems",
                        "q6_understands", "q6_potential"],
         "qtype": "likert_table"},
        {"id": "q7", "y_start": 0.58, "y_end": 0.89,
         "questions": ["q7_timely_info"],
         "qtype": "single_choice"},
    ],
    3: [
        {"id": "q8", "y_start": 0.09, "y_end": 0.26,
         "questions": ["q8_miss_info"],
         "qtype": "single_choice"},
        {"id": "q9", "y_start": 0.22, "y_end": 0.43,
         "questions": ["q9_selections", "q9_other"],
         "qtype": "multi_select"},
        {"id": "q10", "y_start": 0.38, "y_end": 0.67,
         "questions": ["q10_selections", "q10_other"],
         "qtype": "multi_select"},
        {"id": "q11", "y_start": 0.62, "y_end": 0.86,
         "questions": ["q11_selections", "q11_other"],
         "qtype": "multi_select"},
    ],
    4: [
        {"id": "q12", "y_start": 0.08, "y_end": 0.37,
         "questions": ["q12_supervisor", "q12_morning_meetings",
                        "q12_town_hall", "q12_phone_call",
                        "q12_text_sms", "q12_bulletin_board",
                        "q12_email", "q12_visix"],
         "qtype": "likert_table"},
        {"id": "q13", "y_start": 0.31, "y_end": 0.47,
         "questions": ["q13_email_freq"],
         "qtype": "single_choice"},
        {"id": "q14", "y_start": 0.43, "y_end": 0.60,
         "questions": ["q14_awareness"],
         "qtype": "single_choice"},
        {"id": "q15", "y_start": 0.56, "y_end": 0.74,
         "questions": ["q15_comfort"],
         "qtype": "single_choice"},
        {"id": "q16", "y_start": 0.70, "y_end": 0.86,
         "questions": ["q16_feedback_ease"],
         "qtype": "single_choice"},
    ],
    5: [
        {"id": "q17", "y_start": 0.09, "y_end": 0.25,
         "questions": ["q17_feedback_action"],
         "qtype": "single_choice"},
        {"id": "q18", "y_start": 0.20, "y_end": 0.77,
         "questions": ["q18_supervisor_person", "q18_anonymous",
                        "q18_direct_email", "q18_official_channel",
                        "q18_morning_meetings", "q18_town_hall",
                        "q18_point_of_contact",
                        "q18_other_text", "q18_other_rating"],
         "qtype": "likert_table"},
        {"id": "q19", "y_start": 0.67, "y_end": 0.84,
         "questions": ["q19_feel_important"],
         "qtype": "single_choice",
         "continues_on_next_page": True},
    ],
    6: [
        {"id": "q19_cont", "y_start": 0.10, "y_end": 0.21,
         "questions": ["q19_feel_important"],
         "qtype": "single_choice",
         "continuation": True},
        {"id": "q20", "y_start": 0.16, "y_end": 0.77,
         "questions": ["q20_bulletin_boards", "q20_visix_updates",
                        "q20_sms_alerts", "q20_state_phone",
                        "q20_town_hall", "q20_clear_responsibility",
                        "q20_reduce_repeated", "q20_weekly_digest",
                        "q20_training_tools", "q20_replace_computers",
                        "q20_kiosks", "q20_sha_mobile_phone"],
         "qtype": "likert_table"},
        {"id": "q21", "y_start": 0.72, "y_end": 0.94,
         "questions": ["q21_comments"],
         "qtype": "text"},
    ],
}


def _crop_region(img: np.ndarray, y_start_frac: float, y_end_frac: float,
                 x_start_frac: float = 0.0, x_end_frac: float = 1.0) -> np.ndarray:
    """Crop an image using fractional coordinates."""
    h, w = img.shape[:2]
    y1 = max(0, int(h * y_start_frac))
    y2 = min(h, int(h * y_end_frac))
    x1 = max(0, int(w * x_start_frac))
    x2 = min(w, int(w * x_end_frac))
    return img[y1:y2, x1:x2]


def _detect_table_rows(crop: np.ndarray, n_data_rows: int
                       ) -> tuple[tuple[int, int], list[tuple[int, int]]]:
    """
    Locate the header row and data rows in a table crop.

    Returns (header_bounds, data_rows) where header_bounds is
    (y_start, y_end) for the column-header row and data_rows
    is a list of (y_start, y_end) for each data row.
    """
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
    h, w = gray.shape

    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    row_dark = np.sum(binary, axis=1) / 255

    content_mask = row_dark > 80
    content_ys = np.where(content_mask)[0]
    if len(content_ys) < 10:
        return (0, 0), []

    table_top = int(content_ys[0])
    table_bottom = int(content_ys[-1])

    smoothed = np.convolve(row_dark, np.ones(5) / 5, mode="same")

    header_end = table_top
    found_peak = False
    for y in range(table_top, min(table_top + h // 3, h)):
        if smoothed[y] > 150:
            found_peak = True
        if found_peak and smoothed[y] < 40:
            header_end = y
            break

    if header_end == table_top:
        header_end = table_top + (table_bottom - table_top) // (n_data_rows + 2)

    header_bounds = (max(0, table_top - 3), header_end)

    data_top = header_end
    data_bottom = table_bottom
    data_height = data_bottom - data_top

    if data_height < n_data_rows * 10:
        return header_bounds, []

    gaps: list[int] = []
    window = max(3, data_height // (n_data_rows * 4))
    for y in range(data_top + window, data_bottom - window):
        local = np.mean(smoothed[y - window:y + window])
        if local < 30:
            if not gaps or y - gaps[-1] > data_height // (n_data_rows * 2):
                gaps.append(y)

    rows: list[tuple[int, int]] = []
    if len(gaps) >= n_data_rows - 1:
        boundaries = [data_top] + gaps[:n_data_rows - 1] + [data_bottom]
        for i in range(len(boundaries) - 1):
            rows.append((boundaries[i], boundaries[i + 1]))
    else:
        row_h = data_height / n_data_rows
        for i in range(n_data_rows):
            y1 = int(data_top + i * row_h)
            y2 = int(data_top + (i + 1) * row_h)
            rows.append((y1, y2))

    return header_bounds, rows


MULTI_SELECT_ITEMS: dict[str, list[str]] = {
    "q9": ["Training", "HR updates", "Safety messages",
           "License reminders", "Daily work plans", "Other", "None of the above"],
    "q10": ["Daily work plans", "Safety alerts and emergency messages",
            "Weather-related updates affecting work", "Work or operational updates",
            "Equipment or fleet updates", "Training or skill-building opportunities",
            "HR updates (pay, leave, benefits, policies)",
            "License or certification reminders", "SHA or community events",
            "Employee wellness programs or available resources",
            "Career development opportunities", "Other"],
    "q11": ["Face-to-face communication with supervisor", "Morning meetings",
            "Town Hall meetings", "Phone call", "Text/SMS",
            "Bulletin board / flyers", "Email", "Visix overhead screens", "Other"],
}


def _detect_checkbox_items(crop: np.ndarray, n_items: int) -> list[tuple[int, int]]:
    """
    Locate individual checkbox-item lines in a multi-select crop.

    Strategy: detect all distinct text lines in the crop, then take
    the LAST *n_items* lines (the title / overlap content is at the
    top so the actual checkbox items are at the bottom).
    """
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
    h, w = gray.shape

    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    row_dark = np.sum(binary, axis=1) / 255

    content_mask = row_dark > 30
    lines: list[tuple[int, int]] = []
    in_line = False
    line_start = 0
    for y in range(h):
        if content_mask[y] and not in_line:
            line_start = y
            in_line = True
        elif not content_mask[y] and in_line:
            if y - line_start > 5:
                lines.append((line_start, y))
            in_line = False
    if in_line and h - line_start > 5:
        lines.append((line_start, h))

    if len(lines) == 0:
        return []

    if len(lines) > n_items:
        line_heights = [ye - ys for ys, ye in lines]
        median_h = sorted(line_heights)[len(line_heights) // 2]

        gaps_bottom: list[tuple[int, int]] = []
        for i in range(len(lines) - 1):
            gap_size = lines[i + 1][0] - lines[i][1]
            gaps_bottom.append((i, gap_size))

        lower_start = max(0, len(lines) - n_items - 3)
        lower_gaps = [(idx, gs) for idx, gs in gaps_bottom if idx >= lower_start]
        if lower_gaps:
            biggest_lower = max(lower_gaps, key=lambda x: x[1])
            if biggest_lower[1] > median_h * 0.5:
                lines = lines[:biggest_lower[0] + 1]

    if len(lines) < n_items:
        items_top = lines[0][0]
        items_bottom = lines[-1][1]
        item_h = (items_bottom - items_top) / n_items
        return [(max(0, int(items_top + i * item_h) - 2),
                 min(h, int(items_top + (i + 1) * item_h) + 2))
                for i in range(n_items)]

    item_lines = lines[-n_items:]
    rows: list[tuple[int, int]] = []
    for i, (ys, ye) in enumerate(item_lines):
        pad_top = max(0, ys - 3)
        if i + 1 < len(item_lines):
            pad_bot = min(h, item_lines[i + 1][0])
        else:
            pad_bot = min(h, ye + 5)
        rows.append((pad_top, pad_bot))

    return rows


FIRST_Q_TO_SURVEY_PAGE: dict[int, int] = {
    1: 2, 2: 2, 3: 2, 4: 2,
    5: 2,
    8: 3, 9: 3,
    12: 4, 13: 4,
    17: 5, 18: 5,
    19: 6, 20: 6, 21: 6,
}


def _identify_survey_pages(page_paths: list[Path]) -> dict[Path, int]:
    """
    Identify which survey page (1-6) each scan page corresponds to.

    Uses a single VLM call sending the top strip of every non-cover page.
    Returns a mapping from page_path to survey page number.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    content: list[dict] = []
    page_labels: list[str] = []

    for pp in page_paths:
        img = cv2.imread(str(pp))
        if img is None:
            continue
        h = img.shape[0]
        top_strip = img[0:int(h * 0.15), :]
        _, buf = cv2.imencode(".png", top_strip)
        b64 = base64.b64encode(buf).decode("utf-8")
        label = pp.stem
        page_labels.append(label)
        content.append({"type": "text", "text": f"--- {label} ---"})
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
                "detail": "low",
            },
        })

    prompt = (
        "These are the TOP strips of scanned survey pages.\n"
        "The SHA survey has pages numbered 1-6:\n"
        "  Page 1 = cover (no questions)\n"
        "  Page 2 = Q1-Q7 (starts with 'What is your current role')\n"
        "  Page 3 = Q8-Q11 (starts with 'How often do you miss')\n"
        "  Page 4 = Q12-Q16 (starts with 'Instruction: Please rate')\n"
        "  Page 5 = Q17-Q19 (starts with 'When you give feedback')\n"
        "  Page 6 = Q19 cont + Q20-Q21 (starts with 'Somewhat/Mostly/Very much' or 'How useful')\n\n"
        "For each image, identify which SURVEY page (1-6) it is.\n"
        "Return JSON: {\"<page_label>\": <survey_page_number>, ...}"
    )
    content.insert(0, {"type": "text", "text": prompt})

    schema = {
        "type": "object",
        "properties": {
            label: {"type": "integer", "enum": [1, 2, 3, 4, 5, 6]}
            for label in page_labels
        },
        "required": page_labels,
        "additionalProperties": False,
    }

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You identify survey pages from their top strip."},
            {"role": "user", "content": content},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "page_ids", "strict": True, "schema": schema},
        },
        temperature=0.0,
        max_completion_tokens=256,
    )
    mapping_raw = json.loads(resp.choices[0].message.content)

    result: dict[Path, int] = {}
    for pp in page_paths:
        label = pp.stem
        if label in mapping_raw:
            result[pp] = mapping_raw[label]
    return result


def segment_pages(
    page_paths: list[Path],
    output_dir: Path,
) -> list[dict]:
    """
    Segment page images into individual question crops.

    Automatically identifies which survey page each scan page represents,
    handling both 6-page and 3-page (single-sided) scans.

    Returns a list of dicts, each with:
      - id:        region identifier (e.g. "q5", "q12")
      - crop_path: Path to the cropped image
      - questions: list of field names this crop covers
      - qtype:     question type (text/single_choice/multi_select/likert_table)
      - row_crops: (for tables) list of dicts with row_index and row_crop_path
      - continuation: True if this continues a previous page's question
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = page_paths[0].stem.rsplit("_page_", 1)[0]

    page_map = _identify_survey_pages(page_paths)
    print(f"  Page mapping: { {p.stem: v for p, v in page_map.items()} }")

    segments: list[dict] = []

    for page_path in page_paths:
        survey_page = page_map.get(page_path)
        if survey_page is None:
            continue
        page_num = survey_page

        if page_num not in QUESTION_REGIONS:
            continue

        img = cv2.imread(str(page_path))
        if img is None:
            continue

        for region in QUESTION_REGIONS[page_num]:
            crop = _crop_region(img, region["y_start"], region["y_end"])

            crop_filename = f"{stem}_{region['id']}.png"
            crop_path = output_dir / crop_filename
            cv2.imwrite(str(crop_path), crop)

            segment = {
                "id": region["id"],
                "crop_path": crop_path,
                "questions": region["questions"],
                "qtype": region["qtype"],
                "continuation": region.get("continuation", False),
                "continues_on_next_page": region.get("continues_on_next_page", False),
            }

            if region["qtype"] == "multi_select":
                base_id = region["id"]
                if base_id in MULTI_SELECT_ITEMS:
                    item_labels = MULTI_SELECT_ITEMS[base_id]
                    item_rows = _detect_checkbox_items(crop, len(item_labels))
                    item_crops: list[dict] = []
                    for ii, (y1, y2) in enumerate(item_rows):
                        item_img = crop[y1:y2, :]
                        item_fn = f"{stem}_{base_id}_item{ii:02d}.png"
                        item_path = output_dir / item_fn
                        cv2.imwrite(str(item_path), item_img)
                        item_crops.append({
                            "item_index": ii,
                            "item_label": item_labels[ii],
                            "item_crop_path": item_path,
                        })
                    segment["item_crops"] = item_crops

            if region["qtype"] == "likert_table":
                n_table_items = len([q for q in region["questions"]
                                     if not q.endswith("_text") and not q.endswith("_rating")])
                header_bounds, table_rows = _detect_table_rows(crop, n_table_items)

                if header_bounds[1] > header_bounds[0]:
                    hdr_img = crop[header_bounds[0]:header_bounds[1], :]
                    hdr_fn = f"{stem}_{region['id']}_header.png"
                    hdr_path = output_dir / hdr_fn
                    cv2.imwrite(str(hdr_path), hdr_img)
                    segment["header_crop_path"] = hdr_path

                row_crops: list[dict] = []
                for ri, (y1, y2) in enumerate(table_rows):
                    row_img = crop[y1:y2, :]
                    row_filename = f"{stem}_{region['id']}_row{ri:02d}.png"
                    row_path = output_dir / row_filename
                    cv2.imwrite(str(row_path), row_img)
                    row_crops.append({
                        "row_index": ri,
                        "row_crop_path": row_path,
                    })
                segment["row_crops"] = row_crops

            segments.append(segment)

    return segments
