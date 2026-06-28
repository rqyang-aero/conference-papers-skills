#!/usr/bin/env python3
"""Archive external paper figures into the site data directory."""

from __future__ import annotations

import argparse
import copy
import mimetypes
import re
import urllib.parse
import urllib.request
from pathlib import Path

from conference_lib import configured_paths, load_all_papers, load_config, paper_path, slugify, write_json


IMAGE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


def is_valid_image_bytes(data: bytes, content_type: str = "") -> bool:
    if not data:
        return False
    kind = content_type.split(";", 1)[0].strip().lower()
    if kind in IMAGE_EXTENSIONS:
        return True
    head = data[:32].lstrip()
    return (
        head.startswith(b"\x89PNG")
        or head.startswith(b"\xff\xd8\xff")
        or head.startswith(b"GIF")
        or (head.startswith(b"RIFF") and data[8:12] == b"WEBP")
        or head.startswith(b"<svg")
        or head.startswith(b"<?xml")
    )


def image_extension(url: str, content_type: str = "") -> str:
    kind = content_type.split(";", 1)[0].strip().lower()
    if kind in IMAGE_EXTENSIONS:
        return IMAGE_EXTENSIONS[kind]
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    guessed, _ = mimetypes.guess_type(url)
    return IMAGE_EXTENSIONS.get(str(guessed), ".png")


def fetch_image(url: str, timeout: int = 20) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "conference-papers-skill/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("content-type", "")
        data = response.read()
    if not is_valid_image_bytes(data, content_type):
        raise ValueError(f"not an image response: {content_type or 'unknown content type'}")
    return data, content_type


def figure_collections(paper: dict) -> list[list[dict]]:
    collections = []
    if isinstance(paper.get("figures"), list):
        collections.append(paper["figures"])
    note = paper.get("note") or {}
    if isinstance(note.get("figures"), list):
        collections.append(note["figures"])
    return collections


def local_path_for(paper_id: str, filename: str) -> str:
    return f"../../assets/papers/{paper_id}/{filename}"


def resolve_local_path(data_dir: Path, local_path: str) -> Path:
    normalized = local_path.replace("\\", "/")
    while normalized.startswith("../"):
        normalized = normalized[3:]
    if normalized.startswith("data/"):
        normalized = normalized[5:]
    return data_dir / normalized


def archive_paper_figures(data_dir: Path, paper: dict, timeout: int = 20, force: bool = False) -> dict:
    archived = copy.deepcopy(paper)
    paper_id = str(archived.get("id") or slugify(str(archived.get("title") or "paper")))
    asset_dir = data_dir / "assets" / "papers" / paper_id
    url_cache: dict[str, str] = {}
    counter = 0
    for figures in figure_collections(archived):
        for figure in figures:
            url = str(figure.get("url") or "")
            if not url:
                continue
            if figure.get("local_path") and not force:
                local_file = resolve_local_path(data_dir, str(figure["local_path"]))
                if local_file.exists():
                    continue
            if url in url_cache and not force:
                figure["local_path"] = url_cache[url]
                continue
            data, content_type = fetch_image(url, timeout=timeout)
            counter += 1
            stem = slugify(str(figure.get("number") or figure.get("caption") or f"figure-{counter}"), max_len=48)
            filename = f"{stem or f'figure-{counter}'}{image_extension(url, content_type)}"
            asset_dir.mkdir(parents=True, exist_ok=True)
            destination = asset_dir / filename
            if destination.exists() and force:
                destination.unlink()
            if not destination.exists():
                destination.write_bytes(data)
            figure["local_path"] = local_path_for(paper_id, filename)
            url_cache[url] = figure["local_path"]
    return archived


def main() -> None:
    parser = argparse.ArgumentParser(description="Download paper figure URLs into data/assets and fill local_path.")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--config", type=Path, help="Optional config JSON override.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--force", action="store_true", help="Re-download figures even when local_path already exists.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    config = load_config(skill_dir, site_dir=Path.cwd(), config_path=args.config)
    default_data, _ = configured_paths(config)
    data_dir = args.data or default_data
    checked = 0
    archived_count = 0
    for paper in load_all_papers(data_dir):
        if args.limit and checked >= args.limit:
            break
        checked += 1
        try:
            updated = archive_paper_figures(data_dir, paper, timeout=args.timeout, force=args.force)
        except Exception as exc:
            print(f"skip {paper.get('title')}: {exc}")
            continue
        if updated != paper:
            write_json(paper_path(data_dir, updated["id"]), updated)
            archived_count += 1
    print(f"archived figures for {archived_count} of {checked} checked papers")


if __name__ == "__main__":
    main()
