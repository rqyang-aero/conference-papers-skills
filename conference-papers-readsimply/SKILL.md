---
name: conference-papers-readsimply
description: Use when Codex needs to generate abstract-only Obsidian Markdown notes from one or more data/papers/*.json files by reading arXiv HTML abstract metadata when available, without reading the full paper. Trigger for requests like "Use $conference-papers-readsimply 简读 data/papers/xxx.json", "批量简读 data/papers/*.json", or "generate simple abstract md notes"; this skill is independent from website note JSON and dist build.
---

# Conference Papers ReadSimply

Generate standalone Obsidian Markdown notes from `data/papers/*.json` using abstract only. Prefer arXiv HTML for the abstract and page metadata when available, but stop at the abstract block. This is a lightweight Markdown export workflow: do not edit `paper["note"]`, do not modify `data/papers/*.json`, do not run website validation/build scripts, and do not treat the result as site data.

This skill is adapted from `conference-papers-read2md`, but it intentionally does less work to save time and tokens.

## Workflow

1. Resolve the site root and target paper JSON input.
   - Accept a single JSON path, multiple JSON paths, a paper id/title substring, a glob such as `data/papers/*.json`, or a directory such as `data/papers/`.
   - For one paper, run:

```bash
python3 scripts/paper_json_context.py data/papers/PAPER_ID.json
```

   - For batch input, run:

```bash
python3 scripts/batch_paper_json_context.py data/papers/*.json
python3 scripts/batch_paper_json_context.py data/papers/
```

2. Read the helper JSON output.
   - `output_dir`: normally `data/_inbox/{paper-id}`
   - `simple_note_path`: normally `data/_inbox/{paper-id}/{MethodName}-simple.md` (for example, `MethodName-simple.md`)
   - `primary_source`: should be `arxiv_html_abstract` when an arXiv HTML URL is available.
   - use `suggested_method_name` as a starting point, but correct it if the title clearly uses a different method/model name.

3. Read abstract only.
   - 只阅读 abstract；this skill is for abstract-only reading.
   - Read arXiv HTML abstract metadata first when `arxiv_html_url` is available.
   - 只读取 arXiv HTML 的摘要和元信息：title, authors, date, and abstract.
   - Use the helper below when possible:

```bash
python3 scripts/arxiv_html_metadata.py "$arxiv_html_url"
```

   - Combine arXiv HTML metadata with paper JSON metadata: use arXiv HTML for title/authors/date/abstract when it is more complete, and use paper JSON for venue, year, topics, project/code links, and output paths.
   - If arXiv HTML is unavailable or has no abstract block, fall back to the paper JSON `abstract`, arXiv abs/API metadata, or a conference detail page abstract.
   - Do not read arXiv HTML body after the abstract.
   - Do not download or parse PDFs.
   - Do not read method, experiment, appendix, figures, tables, formulas, or project page body content.
   - If no abstract is available, stop that paper and record a clear failure.

4. Write the Markdown note using `assets/paper-note-template.md`.
   - Fill YAML frontmatter with paper JSON metadata where available, refined by arXiv HTML metadata when available.
   - Fill the metadata table with authors, venue as `{Venue} {Year}`, categories/topics from the paper JSON, and dates/links from the best available metadata.
   - Write one concise Chinese sentence summarizing the abstract. Do not invent method details beyond the abstract.
   - For batch mode, process papers one by one. A failure for one paper must not block other papers; report success and failure lists at the end.

5. Keep the note lightweight.
   - Output only frontmatter, title, `## 元信息`, and `## 一句话总结`.
   - Do not create `assets/`.
   - Do not download images.
   - Do not create concept notes or Obsidian MOCs.

## Quality Requirements

- abstract only: never spend tokens on full-paper reading for this skill.
- Prefer arXiv HTML abstract metadata when available, but never continue into Introduction, Method, Experiments, Appendix, figures, tables, or formulas.
- Preserve only metadata and one-sentence summary.
- The summary must be based on the extracted abstract and should stay under 50 Chinese characters when possible.
- Batch output should use `{MethodName}-simple.md`, overwriting existing simple notes if regenerated, but never overwriting `{MethodName}.md` deep-reading notes.
- Never write a deep-reading skeleton. If the abstract is missing, report the failure instead of filling placeholders.

## Important Non-Goals

- Do not modify `data/papers/*.json`.
- Do not generate or validate `paper["note"]`.
- Do not call `../conference-papers/scripts/build_site.py`, `validate_notes.py`, or `resolve_links.py`.
- Do not refresh Obsidian MOCs or run git automation.
- Do not read the full paper as a fallback.

## Bundled Resources

- `assets/paper-note-template.md`: abstract-only Obsidian note template.
- `scripts/paper_json_context.py`: normalize one paper JSON into readsimply source/output context.
- `scripts/batch_paper_json_context.py`: expand JSON paths, globs, directories, ids, or title matches into a best-effort batch context.
- `scripts/arxiv_html_metadata.py`: optional helper to extract title, authors, date, and abstract from arXiv HTML only.
