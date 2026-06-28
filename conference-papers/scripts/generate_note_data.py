#!/usr/bin/env python3
"""Generate or update structured note data for one paper JSON file."""

from __future__ import annotations

import argparse
from pathlib import Path

from conference_lib import configured_paths, generate_draft_note, load_all_papers, load_config, load_json, resolve_internal_links, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate paper note JSON data.")
    parser.add_argument("--paper", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--data", type=Path, help="Optional data root used for internal link resolution.")
    parser.add_argument("--config", type=Path, help="Optional config JSON override.")
    parser.add_argument("--draft", action="store_true", help="Generate a lightweight draft note.")
    args = parser.parse_args()

    paper = load_json(args.paper, default={})
    if not isinstance(paper, dict) or not paper.get("title"):
        parser.error(f"{args.paper} is not a valid paper JSON file")

    if args.draft:
        paper["note"] = generate_draft_note(paper)
    else:
        paper["reading_request"] = {
            "status": "needs_codex_paper_reader",
            "instruction": "Use the paper-reader skill to read the full paper, verify all figures/tables/formulas, then replace note with high-quality structured sections.",
        }

    skill_dir = Path(__file__).resolve().parents[1]
    config = load_config(skill_dir, site_dir=Path.cwd(), config_path=args.config)
    default_data, _ = configured_paths(config)
    all_papers = load_all_papers(args.data or default_data) if (args.data or default_data) else []
    if all_papers:
        paper["note"] = resolve_internal_links(paper.get("note") or {}, all_papers)

    out = args.out or args.paper
    write_json(out, paper)
    print(f"wrote note data -> {out}")


if __name__ == "__main__":
    main()
