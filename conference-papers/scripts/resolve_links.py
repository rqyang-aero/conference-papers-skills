#!/usr/bin/env python3
"""Resolve related/future-work references to internal paper IDs."""

from __future__ import annotations

import argparse
from pathlib import Path

from conference_lib import configured_paths, load_all_papers, load_config, resolve_internal_links, save_paper


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve stored paper note links against the site paper corpus.")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--config", type=Path, help="Optional config JSON override.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    config = load_config(skill_dir, site_dir=Path.cwd(), config_path=args.config)
    default_data, _ = configured_paths(config)
    data_dir = args.data or default_data
    papers = load_all_papers(data_dir)
    for paper in papers:
        if paper.get("note"):
            paper["note"] = resolve_internal_links(paper["note"], papers)
            save_paper(data_dir, paper)
    print(f"resolved links for {len(papers)} papers")


if __name__ == "__main__":
    main()
