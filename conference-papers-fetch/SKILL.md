---
name: conference-papers-fetch
description: Use when the user asks to fetch, crawl, collect, scrape, or refresh conference paper candidates from CVPR/CVF pages, RSS/Atom feeds, manual paper lists, or topic filters before reading or building the site.
---

# Conference Papers Fetch

Use this thin entrypoint for the fetch stage of the conference paper website. The implementation lives in `../conference-papers`; do not duplicate scripts here.

## Workflow

1. Resolve the site root and ensure it has or will have `data/`.
2. Read defaults from `../conference-papers/config/user-config.json`; allow a site-local `config/user-config.local.json` to override conference, year, topics, source URL, and paths.
3. Read the core source rules if needed: `../conference-papers/references/source-adapters.md`.
4. For a conference page, RSS/Atom feed, or manual JSON list, run one of:

```bash
python3 ../conference-papers/scripts/add_papers.py --draft
python3 ../conference-papers/scripts/add_papers.py --conference CVPR --year 2026 --topic VLA --url "https://cvpr.thecvf.com/virtual/2026/papers.html" --data data --draft
python3 ../conference-papers/scripts/crawl_conference.py --conference CVPR --year 2026 --url "https://cvpr.thecvf.com/virtual/2026/papers.html" --topics VLA Humanoid locomotion --out data/conferences/cvpr-2026.json
```

5. When the conference page gives weak metadata or misses PDFs, run arXiv enrichment:

```bash
python3 ../conference-papers/scripts/enrich_arxiv.py --data data
```

6. If the user provides several topics, preserve multi-topic membership. A paper can belong to more than one topic.
7. Stop after fetching unless the user also asks to read notes or build the site.

## Output

Fetch should update `data/papers/*.json` and `data/conferences/*.json`. Report how many papers were added or merged.
