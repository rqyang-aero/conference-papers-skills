# Source Adapter Rules

Use one source adapter per source shape. Keep adapters deterministic and low-dependency.

## Supported V1 Sources

| Source | Input | Script behavior |
|---|---|---|
| CVF/CVPR virtual pages | HTML URL or file | Extract title, authors, detail URL, PDF URL, abstract when present |
| RSS/Atom | Feed URL or file | Extract title, link, summary/description, author, source URL |
| Manual JSON | Local JSON list | Trust provided title/authors/url/pdf/abstract fields |

## Unified Metadata Flow

Conference pages should be treated as discovery sources first. After `scripts/add_papers.py` stores title/authors/detail URL candidates, run:

```bash
python3 scripts/enrich_arxiv.py --data data
```

The arXiv enrichment step searches by title, scores candidates by title similarity and author overlap, and fills `arxiv_id`, `arxiv_url`, missing `abstract`, missing `pdf_url`, and missing `authors`. It preserves the original conference `source`, `source_url`, and `detail_url`.

## Manual JSON Format

```json
[
  {
    "title": "Paper title",
    "authors": ["A. Author", "B. Author"],
    "url": "https://arxiv.org/abs/2601.00001",
    "pdf_url": "https://arxiv.org/pdf/2601.00001",
    "abstract": "Short abstract or note."
  }
]
```

## Adding New Sources

Add a parser in `scripts/conference_lib.py` and call it from `parse_source_text`. Preserve the normalized paper schema from `references/site-schema.md`.

For SIGGRAPH/RSS-style pages, prefer an RSS/Atom feed if available. If the website uses a custom HTML layout, add the smallest parser that extracts title, authors, and detail URL, then rely on `enrich_arxiv.py` for abstract/PDF when possible. Do not hard-code one year's DOM unless the site has no stable markers.

## Topic Classification

Topic classification is recall-oriented. It should collect candidates, not make final research judgments. If the user cares about precision, Codex should review the matched papers and edit the `topics` list manually.
