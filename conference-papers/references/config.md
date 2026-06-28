# Configuration

The core skill ships with `config/user-config.json`. Keep durable defaults there and put personal or per-site overrides in `config/user-config.local.json`.

## Precedence

Lowest to highest:

1. Built-in script defaults.
2. `conference-papers/config/user-config.json`.
3. `conference-papers/config/user-config.local.json`.
4. Site-local `config/user-config.local.json` from the current working directory.

## Main Fields

```json
{
  "site": {
    "title": "Conference Papers",
    "data_dir": "data",
    "output_dir": "dist"
  },
  "defaults": {
    "conference": "CVPR",
    "year": 2026,
    "topics": ["VLA", "Humanoid", "locomotion", "loco-manipulation"]
  },
  "sources": [
    {
      "name": "cvpr-2026",
      "conference": "CVPR",
      "year": 2026,
      "type": "cvf",
      "url": "https://cvpr.thecvf.com/virtual/2026/papers.html"
    }
  ],
  "topic_keywords": {
    "VLA": ["vla", "vision-language-action"]
  }
}
```

## CLI Behavior

If CLI arguments are omitted, scripts fall back to config:

- `add_papers.py --draft` uses default conference/year/topics/source/data path.
- `build_site.py` uses default data and output paths.
- `classify_topics.py`, `enrich_arxiv.py`, `enrich_fulltext.py`, `archive_figures.py`, `validate_notes.py`, and `resolve_links.py` use default data path.

Explicit CLI flags always win over config values for that invocation.
