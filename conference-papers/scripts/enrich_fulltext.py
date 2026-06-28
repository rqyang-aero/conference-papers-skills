#!/usr/bin/env python3
"""Lightweight metadata enrichment from available HTML pages."""

from __future__ import annotations

import argparse
from pathlib import Path

from conference_lib import configured_paths, extract_figures_from_html, extract_project_urls, fetch_text, load_all_papers, load_config, save_paper


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich papers with figures and project links from HTML pages.")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--config", type=Path, help="Optional config JSON override.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    config = load_config(skill_dir, site_dir=Path.cwd(), config_path=args.config)
    default_data, _ = configured_paths(config)
    data_dir = args.data or default_data
    enriched = 0
    for paper in load_all_papers(data_dir):
        if args.limit and enriched >= args.limit:
            break
        url = paper.get("detail_url") or paper.get("url")
        if not url or url.lower().endswith(".pdf"):
            continue
        try:
            text = fetch_text(url)
        except Exception as exc:
            print(f"skip {paper.get('title')}: {exc}")
            continue
        figures = extract_figures_from_html(text, url)
        if figures and not paper.get("figures"):
            paper["figures"] = figures
        projects = extract_project_urls(text)
        if projects and not paper.get("project_url"):
            paper["project_url"] = projects[0]
        save_paper(data_dir, paper)
        enriched += 1
    print(f"enriched {enriched} papers")


if __name__ == "__main__":
    main()
