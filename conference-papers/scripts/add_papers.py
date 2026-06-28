#!/usr/bin/env python3
"""Add papers to the structured site data store."""

from __future__ import annotations

import argparse
from pathlib import Path

from conference_lib import (
    configured_defaults,
    configured_paths,
    fetch_text,
    find_config_source,
    generate_draft_note,
    load_config,
    parse_manual_json,
    parse_source_text,
    save_paper,
    update_conference_index,
)


def topics_from_args(args: argparse.Namespace) -> list[str]:
    topics: list[str] = []
    for item in args.topic or []:
        topics.append(item)
    for item in args.topics or []:
        topics.append(item)
    return topics


def main() -> None:
    parser = argparse.ArgumentParser(description="Add or merge conference papers.")
    parser.add_argument("--conference")
    parser.add_argument("--year", type=int)
    parser.add_argument("--topic", action="append", default=[])
    parser.add_argument("--topics", nargs="*", default=[])
    parser.add_argument("--url", help="CVF/RSS/Atom/manual JSON source.")
    parser.add_argument("--manual", type=Path, help="Local manual JSON paper list.")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--config", type=Path, help="Optional config JSON override.")
    parser.add_argument("--source-name", default="", help="Named source from config/user-config.json.")
    parser.add_argument("--draft", action="store_true", help="Generate draft note data while adding.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    config = load_config(skill_dir, site_dir=Path.cwd(), config_path=args.config)
    default_conference, default_year, default_topics = configured_defaults(config)
    default_data, _ = configured_paths(config)
    conference = args.conference or default_conference
    year = args.year or default_year
    topics = topics_from_args(args) or default_topics
    data_dir = args.data or default_data
    config_source = find_config_source(config, conference, year, args.source_name)
    url = args.url or (config_source or {}).get("url")
    manual_path = args.manual
    if not manual_path and (config_source or {}).get("path"):
        manual_path = Path(str((config_source or {})["path"]))
    if not url and not manual_path:
        parser.error("provide --url/--manual or configure a matching source in config/user-config.json")
    if manual_path:
        text = manual_path.read_text(encoding="utf-8")
        papers = parse_manual_json(text, conference, year, topics, source_url=str(manual_path))
        source_url = str(manual_path)
    else:
        text = fetch_text(str(url))
        papers = parse_source_text(text, str(url), conference, year, topics)
        source_url = str(url)

    saved = []
    for paper in papers:
        if args.draft and not paper.get("note"):
            paper["note"] = generate_draft_note(paper)
        saved.append(save_paper(data_dir, paper))
    update_conference_index(data_dir, conference, year, saved, source_url=source_url)
    print(f"added/merged {len(saved)} papers in {data_dir}")


if __name__ == "__main__":
    main()
