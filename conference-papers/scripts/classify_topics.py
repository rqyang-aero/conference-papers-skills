#!/usr/bin/env python3
"""Classify existing paper JSON files against a topic list."""

from __future__ import annotations

import argparse
from pathlib import Path

from conference_lib import classify_topics, configured_defaults, configured_paths, load_all_papers, load_config, save_paper


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply multi-topic keyword classification to stored papers.")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--topics", nargs="+")
    parser.add_argument("--config", type=Path, help="Optional config JSON override.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    config = load_config(skill_dir, site_dir=Path.cwd(), config_path=args.config)
    _, _, default_topics = configured_defaults(config)
    default_data, _ = configured_paths(config)
    data_dir = args.data or default_data
    topics = args.topics or default_topics
    updated = 0
    for paper in load_all_papers(data_dir):
        hits = classify_topics(paper, topics)
        if hits:
            paper["topics"] = sorted(set(paper.get("topics", []) + hits), key=str.lower)
            save_paper(data_dir, paper)
            updated += 1
    print(f"updated {updated} papers")


if __name__ == "__main__":
    main()
