#!/usr/bin/env python3
"""Fetch and parse a conference source into a conference index JSON file."""

from __future__ import annotations

import argparse
from pathlib import Path

from conference_lib import configured_defaults, configured_paths, fetch_text, find_config_source, load_config, parse_source_text, update_conference_index, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl CVF/CVPR, RSS/Atom, or manual JSON conference sources.")
    parser.add_argument("--conference")
    parser.add_argument("--year", type=int)
    parser.add_argument("--url", help="HTTP(S), file://, or local path source.")
    parser.add_argument("--topics", nargs="*", default=[])
    parser.add_argument("--out", type=Path)
    parser.add_argument("--config", type=Path, help="Optional config JSON override.")
    parser.add_argument("--source-name", default="", help="Named source from config/user-config.json.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    config = load_config(skill_dir, site_dir=Path.cwd(), config_path=args.config)
    default_conference, default_year, default_topics = configured_defaults(config)
    default_data, _ = configured_paths(config)
    conference = args.conference or default_conference
    year = args.year or default_year
    topics = args.topics or default_topics
    config_source = find_config_source(config, conference, year, args.source_name)
    url = args.url or (config_source or {}).get("url")
    if not url:
        parser.error("provide --url or configure a matching source in config/user-config.json")
    out = args.out or (default_data / "conferences" / f"{conference.lower()}-{year}.json")

    text = fetch_text(str(url))
    papers = parse_source_text(text, str(url), conference, year, topics)
    payload = {
        "conference": conference,
        "year": year,
        "source_url": str(url),
        "papers": [{"id": p["id"], "title": p["title"], "topics": p.get("topics", []), "pdf_url": p.get("pdf_url", "")} for p in papers],
    }
    write_json(out, payload)
    data_root = out.parent.parent if out.parent.name == "conferences" else None
    if data_root:
        update_conference_index(data_root, conference, year, papers, source_url=str(url))
    print(f"parsed {len(papers)} papers -> {out}")


if __name__ == "__main__":
    main()
