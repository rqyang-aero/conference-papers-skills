---
name: conference-papers
description: Use when building or maintaining a searchable HTML reading site from conference papers, CVPR/CVF virtual pages, RSS/Atom feeds, manual paper lists, or topic-specific paper collections such as VLA, Humanoid, locomotion, or loco-manipulation.
---

# Conference Papers

Build and maintain a static conference-paper reading site with structured paper data, multi-topic indexing, draft/high-quality note modes, internal paper links, and client-side search.

## Quick Start

Resolve the working site root first. If the user does not specify one, create or use the current workspace directory. Keep generated site state in:

```text
config/user-config.local.json  # optional site-specific override
data/papers/*.json
data/conferences/*.json
dist/
```

Read defaults from `config/user-config.json` in this skill. A site can override defaults by creating `config/user-config.local.json` in the working site root or inside the skill folder.

Use the scripts in this skill directory:

```bash
python3 scripts/add_papers.py --draft
python3 scripts/enrich_arxiv.py
python3 scripts/enrich_fulltext.py
python3 scripts/archive_figures.py
python3 scripts/validate_notes.py
python3 scripts/resolve_links.py
python3 scripts/build_site.py
```

## Workflow

1. Parse the request into `conference`, `year`, one or more `topics`, source URLs/files, data root, output root, and mode.
2. Add or crawl papers:
   - CVF/CVPR virtual page, RSS/Atom feed, or JSON paper list: use `scripts/add_papers.py`.
   - Need only a conference index JSON: use `scripts/crawl_conference.py`.
3. Classify topics:
   - Script classification is keyword recall. If topic relevance matters, review ambiguous papers and edit `topics` in `data/papers/*.json`.
   - A paper may belong to multiple topics; never force it into only one.
4. Generate note data:
   - Use `--draft` only for fast preview. Draft notes are incomplete by design.
   - For final notes, read the full paper with `paper-reader`, preserve the metadata/frontmatter and pre-core-contribution template content, then fill the structured `note` object in the paper JSON.
5. Enrich and resolve:
   - Run `enrich_arxiv.py` after fetching conference candidates to fill arXiv ID, abstract, and PDF URL by title matching.
   - Run `enrich_fulltext.py` to collect figures/project links from available HTML.
   - Run `archive_figures.py` when local image fallback is needed for important papers.
   - Run `validate_notes.py` before publishing final notes.
   - Run `resolve_links.py` after adding related/future work entries.
6. Build the site with `build_site.py`.

## High-Quality Reading Mode

Do not pretend the script has deeply read the paper. For final notes:

1. Use `paper-reader` or equivalent full-paper reading.
2. Include all figures, tables, and important formulas.
3. Keep figures near the section that explains them, not as a detached dump.
4. Write these sections in `paper["note"]`:
   - `summary`
   - `background`
   - `contributions`
   - `method`
   - `figures`
   - `experiments`
   - `critical_thinking`
   - `related_work`
   - `future_work`
5. For `related_work` and `future_work`, use objects with `title` and `text`; `resolve_links.py` will add `paper_id` when the referenced paper is already in the corpus.

Read `references/html-note-style.md` before writing final note content.

## Source Handling

- CVF/CVPR pages: use `crawl_conference.py` or `add_papers.py` with `--url`.
- RSS/Atom feeds: use the same `--url` entrypoint.
- Manual collections: create a JSON list and pass `--manual`.
- Single paper additions: use a one-item manual JSON list.

Read `references/source-adapters.md` before adding a new conference source type.

## Site Data Contract

Use `references/site-schema.md` as the data contract. Keep JSON stable and human-editable. Do not introduce a database, package manager, web framework, or hosted backend unless the user explicitly asks for it.

## Templates and Config

- Edit `assets/site-template/paper-note.html` to change single-paper note HTML.
- Edit `assets/site-template/index.html` and `assets/site-template/collection.html` to change list pages.
- Edit `config/user-config.json` for built-in defaults.
- Prefer a site-local `config/user-config.local.json` for personal conference/year/topic/source overrides.
- Read `references/config.md` before changing configuration behavior.

## Validation

After changes, run:

```bash
python3 tests/test_conference_papers.py
python3 /Users/barry/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

For an end-to-end smoke test:

```bash
python3 scripts/add_papers.py --manual tests/fixtures/manual_papers.json --data /tmp/conference-papers-data --draft
python3 scripts/build_site.py --data /tmp/conference-papers-data --out /tmp/conference-papers-dist
```
