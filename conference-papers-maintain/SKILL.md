---
name: conference-papers-maintain
description: Use when the user asks to maintain an existing conference paper website by adding papers, merging topics, deduplicating records, enriching metadata, fixing related-work links, or rebuilding after updates.
---

# Conference Papers Maintain

Use this thin entrypoint for incremental maintenance. The implementation lives in `../conference-papers`; keep all persistent data in the target site's `data/` directory.

## Workflow

1. Inspect the existing `data/papers/*.json` and `data/conferences/*.json`.
   - Use `../conference-papers/config/user-config.json` and optional site-local `config/user-config.local.json` for default paths, conference, year, topics, and sources.
2. Add or merge new papers:

```bash
python3 ../conference-papers/scripts/add_papers.py --draft
python3 ../conference-papers/scripts/add_papers.py --conference CVPR --year 2026 --topic VLA --url "SOURCE" --data data --draft
```

3. Reclassify topics when topic definitions change:

```bash
python3 ../conference-papers/scripts/classify_topics.py
```

4. Enrich metadata from arXiv when conference pages only provide titles or weak metadata:

```bash
python3 ../conference-papers/scripts/enrich_arxiv.py
```

5. Enrich metadata from available HTML:

```bash
python3 ../conference-papers/scripts/enrich_fulltext.py
```

6. Archive external figure URLs when the user wants local image fallback:

```bash
python3 ../conference-papers/scripts/archive_figures.py --data data
```

7. Validate final note structure and figure references:

```bash
python3 ../conference-papers/scripts/validate_notes.py --data data
```

8. Resolve internal links after related/future work changes:

```bash
python3 ../conference-papers/scripts/resolve_links.py
```

9. Rebuild the site:

```bash
python3 ../conference-papers/scripts/build_site.py
```

## Maintenance Rules

- Merge duplicate papers by title or ID instead of creating duplicates.
- Preserve existing final notes when adding topics or metadata.
- Use `conference-papers-read` for final note upgrades; maintenance should not fake full-paper reading.
