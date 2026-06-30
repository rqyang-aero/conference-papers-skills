#!/usr/bin/env python3
"""Batch paper JSON context helper for conference-papers-readsimply."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import Any

from paper_json_context import load_paper_context, resolve_paper_reference


GLOB_CHARS = set("*?[")


def has_glob(value: str) -> bool:
    return any(char in value for char in GLOB_CHARS)


def expand_one_reference(reference: str | Path, site_dir: Path, data_dir: Path | None = None) -> list[Path]:
    text = str(reference)
    path = Path(text).expanduser()

    if has_glob(text):
        matches = sorted(Path(match).expanduser().resolve() for match in glob.glob(text))
        return [match for match in matches if match.is_file()]

    if path.exists() and path.is_dir():
        return sorted(item.resolve() for item in path.glob("*.json") if item.is_file())

    return [resolve_paper_reference(reference, site_dir=site_dir, data_dir=data_dir)]


def expand_paper_references(
    references: list[str | Path],
    site_dir: str | Path | None = None,
    data_dir: str | Path | None = None,
) -> tuple[list[Path], list[dict[str, str]]]:
    site = Path(site_dir or Path.cwd()).expanduser().resolve()
    data = Path(data_dir).expanduser().resolve() if data_dir else None
    paths: list[Path] = []
    failures: list[dict[str, str]] = []

    for reference in references:
        try:
            paths.extend(expand_one_reference(reference, site, data))
        except Exception as exc:  # noqa: BLE001 - batch mode records per-input failures.
            failures.append({"reference": str(reference), "error": str(exc)})

    return paths, failures


def load_batch_contexts(
    references: list[str | Path],
    site_dir: str | Path | None = None,
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    site = Path(site_dir or Path.cwd()).expanduser().resolve()
    data = Path(data_dir).expanduser().resolve() if data_dir else None
    paths, failures = expand_paper_references(references, site, data)
    seen_ids: set[str] = set()
    items: list[dict[str, Any]] = []

    for path in paths:
        try:
            context = load_paper_context(path, site_dir=site, data_dir=data)
        except Exception as exc:  # noqa: BLE001 - continue best-effort batch processing.
            failures.append({"reference": str(path), "error": str(exc)})
            continue

        paper_id = str(context["id"])
        if paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)
        items.append(context)

    return {
        "count": len(items),
        "failed": len(failures),
        "items": items,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Expand paper JSON inputs and print readsimply batch context.")
    parser.add_argument("papers", nargs="+", help="Paper JSON paths, ids, title substrings, globs, or directories.")
    parser.add_argument("--site", type=Path, default=Path.cwd(), help="Site root. Defaults to current directory.")
    parser.add_argument("--data", type=Path, help="Data root containing papers/. Defaults to SITE/data.")
    args = parser.parse_args()

    result = load_batch_contexts(args.papers, site_dir=args.site, data_dir=args.data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["items"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
