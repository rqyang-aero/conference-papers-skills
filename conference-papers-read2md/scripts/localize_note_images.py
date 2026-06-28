#!/usr/bin/env python3
"""Localize Markdown image URLs for conference-papers-read2md inbox notes.

Adapted from huangkiki/dailypaper-skills `download_note_images.py`.
Changes for this project: always stores images beside the generated inbox note
under `assets/` and rewrites links as Obsidian wikilinks.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(((?:https?|file)://[^)\s]+)\)")
DEFAULT_WIDTH = 600


def image_extension(url: str, content_type: str = "") -> str:
    path = urllib.parse.urlparse(url).path
    ext = Path(path).suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
        return ext
    guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip()) if content_type else ""
    if guessed in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
        return guessed
    return ".png"


def is_image_bytes(data: bytes) -> bool:
    header = data[:64].lstrip()
    return (
        data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"\xff\xd8\xff")
        or data.startswith(b"GIF87a")
        or data.startswith(b"GIF89a")
        or (data.startswith(b"RIFF") and data[8:12] == b"WEBP")
        or header.startswith(b"<svg")
        or header.startswith(b"<?xml")
    )


def fetch_image(url: str, timeout: int = 30) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "conference-papers-read2md/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
        content_type = response.headers.get("content-type", "")
    if not is_image_bytes(data):
        raise ValueError(f"not an image: {url}")
    return data, content_type


def replacement_for(assets_subdir: str, filename: str, width: int) -> str:
    return f"![[{assets_subdir}/{filename}|{width}]]"


def process_note(
    note_path: str | Path,
    assets_subdir: str = "assets",
    width: int = DEFAULT_WIDTH,
    timeout: int = 30,
) -> dict[str, Any]:
    note = Path(note_path)
    text = note.read_text(encoding="utf-8")
    images = list(IMAGE_RE.finditer(text))
    assets_dir = note.parent / assets_subdir
    assets_dir.mkdir(parents=True, exist_ok=True)

    replacements: list[tuple[int, int, str]] = []
    localized = 0
    failed: list[dict[str, str]] = []

    for index, match in enumerate(images, start=1):
        url = match.group(2)
        try:
            data, content_type = fetch_image(url, timeout=timeout)
            ext = image_extension(url, content_type)
            filename = f"{note.stem}_fig{index}{ext}"
            destination = assets_dir / filename
            destination.write_bytes(data)
        except Exception as exc:  # noqa: BLE001 - collect per-image failures.
            failed.append({"url": url, "error": str(exc)})
            continue

        replacements.append((match.start(), match.end(), replacement_for(assets_subdir, filename, width)))
        localized += 1

    if replacements:
        new_text = text
        for start, end, replacement in sorted(replacements, reverse=True):
            new_text = new_text[:start] + replacement + new_text[end:]
        note.write_text(new_text, encoding="utf-8")

    return {
        "note": str(note),
        "assets_dir": str(assets_dir),
        "total": len(images),
        "localized": localized,
        "failed": len(failed),
        "failures": failed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Download inbox note images and rewrite links for Obsidian.")
    parser.add_argument("note", type=Path, help="Markdown note path.")
    parser.add_argument("--assets-subdir", default="assets")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args()

    if not args.note.exists():
        print(f"error: note not found: {args.note}", file=sys.stderr)
        return 2

    result = process_note(args.note, assets_subdir=args.assets_subdir, width=args.width, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.fail_on_error and result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
