#!/usr/bin/env python3
"""Extract abstract-only metadata from arXiv HTML.

Source: created for conference-papers-readsimply.
Changes: reads only arXiv HTML title/authors/date/abstract regions; it does
not parse the paper body or PDF.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


CAPTURE_CLASSES = {
    "title": {"ltx_title_document"},
    "authors": {"ltx_authors"},
    "date": {"ltx_dates"},
    "abstract": {"ltx_abstract"},
}

AUTHOR_IGNORE_CLASSES = {"ltx_author_notes"}
AUTHOR_EXCLUDE_WORDS = {
    "author",
    "academy",
    "center",
    "centre",
    "college",
    "contributed",
    "corresponding",
    "department",
    "institute",
    "lab",
    "laboratory",
    "school",
    "university",
}


def clean_space(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def attr_map(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {key: value or "" for key, value in attrs}


def class_set(attrs: list[tuple[str, str | None]]) -> set[str]:
    return set(attr_map(attrs).get("class", "").split())


def starts_capture(attrs: list[tuple[str, str | None]], capture_name: str) -> bool:
    classes = class_set(attrs)
    return bool(classes & CAPTURE_CLASSES[capture_name])


def clean_title(value: str) -> str:
    return re.sub(r"^Title:\s*", "", clean_space(value), flags=re.IGNORECASE)


def clean_abstract(value: str) -> str:
    value = clean_space(value)
    return re.sub(r"^Abstract\s*", "", value, flags=re.IGNORECASE).strip()


def split_authors(value: str) -> list[str]:
    value = clean_space(value)
    value = re.sub(r"^Authors?:\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\\(?:ast|dagger)\b", "", value)
    value = re.sub(r"[∗*†‡§]+", "", value)
    value = re.sub(r"\s*,\s*", ", ", value)
    parts: list[str] = []
    for part in re.split(r",|\s+ and \s+", value):
        author = clean_space(re.sub(r"\b\d+\b", "", part))
        lower = author.lower()
        if not author:
            continue
        if "@" in author or "http" in lower:
            continue
        if any(word in lower for word in AUTHOR_EXCLUDE_WORDS):
            continue
        if not re.search(r"[A-Za-z]", author):
            continue
        parts.append(author)
    return parts


class ArxivHtmlMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capture: str | None = None
        self._depth = 0
        self._ignore_depth = 0
        self._buffers: dict[str, list[str]] = {
            "title": [],
            "authors": [],
            "date": [],
            "abstract": [],
        }

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._capture:
            if self._capture == "authors" and tag == "br":
                self._buffers["authors"].append(", ")
                return

            self._depth += 1
            if self._ignore_depth:
                self._ignore_depth += 1
                return

            if self._capture == "authors":
                classes = class_set(attrs)
                if tag in {"a", "math", "sup"} or classes & AUTHOR_IGNORE_CLASSES:
                    self._ignore_depth = 1
                    if tag == "sup":
                        self._buffers["authors"].append(", ")
                    return

            if self._capture == "abstract":
                metadata = attr_map(attrs)
                alt_text = metadata.get("alttext") or metadata.get("alt")
                if alt_text:
                    self._buffers["abstract"].append(f" {alt_text} ")
            return

        for capture_name in ("abstract", "title", "authors", "date"):
            if starts_capture(attrs, capture_name):
                self._capture = capture_name
                self._depth = 1
                return

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._capture == "authors" and tag == "br":
            self._buffers["authors"].append(", ")
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self._capture:
            return
        if self._ignore_depth:
            self._ignore_depth -= 1
        self._depth -= 1
        if self._depth <= 0:
            self._capture = None
            self._depth = 0
            self._ignore_depth = 0

    def handle_data(self, data: str) -> None:
        if not self._capture:
            return
        if self._ignore_depth:
            return
        self._buffers[self._capture].append(data)

    def metadata(self, url: str = "") -> dict[str, Any]:
        title = clean_title(" ".join(self._buffers["title"]))
        authors = split_authors(" ".join(self._buffers["authors"]))
        abstract = clean_abstract(" ".join(self._buffers["abstract"]))
        date = clean_space(" ".join(self._buffers["date"]))
        return {
            "url": url,
            "title": title,
            "authors": authors,
            "date": date,
            "abstract": abstract,
        }


def parse_arxiv_html_metadata(html: str, url: str = "") -> dict[str, Any]:
    parser = ArxivHtmlMetadataParser()
    parser.feed(html)
    parser.close()
    metadata = parser.metadata(url=url)
    if not metadata["abstract"]:
        raise ValueError("arXiv HTML abstract block was not found")
    return metadata


def fetch_arxiv_html_metadata(url: str, timeout: int = 30) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "conference-papers-readsimply/1.0 (+https://arxiv.org)",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise RuntimeError(f"failed to fetch arXiv HTML: {exc}") from exc
    return parse_arxiv_html_metadata(html, url=url)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract title, authors, date, and abstract from an arXiv HTML page.",
    )
    parser.add_argument("url", help="arXiv HTML URL, for example https://arxiv.org/html/2601.00001")
    parser.add_argument("--timeout", type=int, default=30, help="Network timeout in seconds.")
    args = parser.parse_args()

    try:
        metadata = fetch_arxiv_html_metadata(args.url, timeout=args.timeout)
    except Exception as exc:  # noqa: BLE001 - CLI should surface concise failures.
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
