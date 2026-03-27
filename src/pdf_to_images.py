"""
Convert scanned PDF pages to PNG images for vision-model processing.
Caches images on disk so repeated runs skip the conversion step.
"""

from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image

from .config import IMAGE_DPI


def pdf_to_images(
    pdf_path: Path,
    cache_dir: Path | None = None,
    dpi: int = IMAGE_DPI,
) -> list[Path]:
    """
    Convert every page of *pdf_path* to a PNG file.

    Returns a list of PNG file paths (one per page), stored in *cache_dir*.
    If the PNGs already exist, the conversion is skipped.
    """
    if cache_dir is None:
        cache_dir = pdf_path.parent / ".image_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    stem = pdf_path.stem
    existing = sorted(cache_dir.glob(f"{stem}_page_*.png"))
    if existing:
        return existing

    pages: list[Image.Image] = convert_from_path(
        str(pdf_path),
        dpi=dpi,
        fmt="png",
    )

    paths: list[Path] = []
    for i, page_img in enumerate(pages, start=1):
        out = cache_dir / f"{stem}_page_{i:02d}.png"
        page_img.save(str(out), "PNG")
        paths.append(out)

    return paths
