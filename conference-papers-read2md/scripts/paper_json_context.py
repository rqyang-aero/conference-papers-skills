#!/usr/bin/env python3
"""Prepare paper JSON context for the conference-papers-read2md skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(?:v\d+)?")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def clean_text(value: object) -> str:
    return str(value or "").strip()


def clean_arxiv_id(value: object) -> str:
    match = ARXIV_ID_RE.search(clean_text(value))
    return match.group(1) if match else ""


def extract_arxiv_id(paper: dict[str, Any]) -> str:
    for key in ("arxiv_id", "arxiv_url", "pdf_url", "url", "detail_url"):
        arxiv_id = clean_arxiv_id(paper.get(key))
        if arxiv_id:
            return arxiv_id
    return ""


def arxiv_abs_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/abs/{arxiv_id}"


def arxiv_pdf_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/pdf/{arxiv_id}"


def arxiv_html_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/html/{arxiv_id}"


def safe_method_name(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "-", value).strip()
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .-_") or "PaperNote"


def suggest_method_name(title: str) -> str:
    prefix = re.split(r"[:：]", title, maxsplit=1)[0].strip()
    if 1 < len(prefix) <= 48 and re.search(r"[A-Za-z0-9]", prefix):
        return safe_method_name(prefix)

    acronym = re.search(r"\b[A-Z][A-Za-z0-9_.-]{1,24}\b", title)
    if acronym:
        return safe_method_name(acronym.group(0))

    words = re.findall(r"[A-Za-z0-9]+", title)[:5]
    return safe_method_name(" ".join(words) if words else "PaperNote")


def unique_urls(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for item in items:
        url = item.get("url", "")
        key = f"{item.get('type', '')}:{url}"
        if url and key not in seen:
            result.append(item)
            seen.add(key)
    return result


def arxiv_search_query(title: str, authors: list[str]) -> str:
    author_part = " ".join(authors[:3])
    return " ".join(part for part in (title, author_part, "arxiv") if part).strip()


def path_relative_to(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def infer_data_dir(paper_path: Path, site_dir: Path, data_dir: Path | None) -> Path:
    if data_dir:
        return data_dir
    if paper_path.parent.name == "papers":
        return paper_path.parent.parent
    return site_dir / "data"


def resolve_paper_reference(reference: str | Path, site_dir: Path | None = None, data_dir: Path | None = None) -> Path:
    site = (site_dir or Path.cwd()).resolve()
    ref = Path(str(reference)).expanduser()
    if ref.exists():
        return ref.resolve()

    papers_dir = (data_dir or site / "data") / "papers"
    direct = papers_dir / f"{reference}.json"
    if direct.exists():
        return direct.resolve()

    needle = str(reference).lower()
    matches: list[Path] = []
    for path in sorted(papers_dir.glob("*.json")):
        try:
            paper = load_json(path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        title = clean_text(paper.get("title")).lower()
        paper_id = clean_text(paper.get("id") or path.stem).lower()
        if needle == paper_id or needle in title:
            matches.append(path)

    if not matches:
        raise FileNotFoundError(f"could not resolve paper JSON: {reference}")
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches[:5])
        raise ValueError(f"paper reference is ambiguous: {reference} ({names})")
    return matches[0].resolve()


def load_paper_context(
    reference: str | Path,
    site_dir: str | Path | None = None,
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    site = Path(site_dir or Path.cwd()).expanduser().resolve()
    data_root_override = Path(data_dir).expanduser().resolve() if data_dir else None
    paper_path = resolve_paper_reference(reference, site, data_root_override)
    paper = load_json(paper_path)

    title = clean_text(paper.get("title"))
    if not title:
        raise ValueError(f"{paper_path} is missing required field: title")

    paper_id = clean_text(paper.get("id")) or paper_path.stem
    authors = [clean_text(author) for author in paper.get("authors") or [] if clean_text(author)]
    arxiv_id = extract_arxiv_id(paper)
    arxiv_url = clean_text(paper.get("arxiv_url")) or (arxiv_abs_url(arxiv_id) if arxiv_id else "")
    pdf_url = clean_text(paper.get("pdf_url")) or (arxiv_pdf_url(arxiv_id) if arxiv_id else "")
    html_url = arxiv_html_url(arxiv_id) if arxiv_id else ""
    query = arxiv_search_query(title, authors)

    candidates: list[dict[str, str]] = []
    if html_url:
        candidates.append({"type": "arxiv_html", "url": html_url})
    if arxiv_url:
        candidates.append({"type": "arxiv_abs", "url": arxiv_url})
    if pdf_url:
        candidates.append({"type": "pdf", "url": pdf_url})
    for key, source_type in (
        ("project_url", "project"),
        ("url", "url"),
        ("detail_url", "detail"),
    ):
        value = clean_text(paper.get(key))
        if value:
            candidates.append({"type": source_type, "url": value})
    if not candidates:
        candidates.append({"type": "arxiv_search", "url": query})

    data_root = infer_data_dir(paper_path, site, data_root_override)
    inbox_dir = data_root / "_inbox" / paper_id
    assets_dir = inbox_dir / "assets"
    venue = clean_text(paper.get("conference") or paper.get("venue") or ("arXiv" if arxiv_id else ""))

    return {
        "id": paper_id,
        "title": title,
        "authors": authors,
        "year": paper.get("year") or "",
        "venue": venue,
        "topics": paper.get("topics") or [],
        "abstract": clean_text(paper.get("abstract")),
        "arxiv_id": arxiv_id,
        "arxiv_url": arxiv_url,
        "arxiv_html_url": html_url,
        "pdf_url": pdf_url,
        "project_url": clean_text(paper.get("project_url")),
        "source_candidates": unique_urls(candidates),
        "primary_source": unique_urls(candidates)[0],
        "arxiv_search_query": query,
        "suggested_method_name": suggest_method_name(title),
        "paper_json": path_relative_to(paper_path, site),
        "output_dir": path_relative_to(inbox_dir, site),
        "assets_dir": path_relative_to(assets_dir, site),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read conference paper JSON and print read2md context.")
    parser.add_argument("paper", help="Paper JSON path, paper id, or title substring.")
    parser.add_argument("--site", type=Path, default=Path.cwd(), help="Site root. Defaults to current directory.")
    parser.add_argument("--data", type=Path, help="Data root containing papers/. Defaults to SITE/data.")
    args = parser.parse_args()

    try:
        context = load_paper_context(args.paper, site_dir=args.site, data_dir=args.data)
    except Exception as exc:  # noqa: BLE001 - CLI should surface concise errors.
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(context, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
