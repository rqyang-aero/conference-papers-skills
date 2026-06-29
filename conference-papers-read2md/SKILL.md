---
name: conference-papers-read2md
description: Use when Codex needs to read a conference paper from data/papers/*.json and generate a standalone Obsidian-compatible deep-reading Markdown note under data/_inbox, with online images by default and optional localization only when needed. Trigger for requests like "Use $conference-papers-read2md 精读 data/papers/xxx.json", "根据 paper JSON 生成 Obsidian md", or "read conference paper JSON to Markdown"; this skill is independent from the conference-papers website note JSON and dist build.
---

# Conference Papers Read2MD

Generate dailypaper-style Obsidian Markdown notes from `data/papers/*.json`. This is a standalone Markdown export workflow: do not edit `paper["note"]`, do not modify `data/papers/*.json`, do not run website validation/build scripts, and do not treat the result as site data.

This skill adapts `huangkiki/dailypaper-skills` paper-reader resources. Preserve its deep-reading style and quality bar; only the input source and output location differ.

## Workflow

1. Resolve the site root and target paper JSON.
   - Accept an explicit JSON path, paper id, or title substring.
   - Run the context helper from this skill directory:

```bash
python3 scripts/paper_json_context.py data/papers/PAPER_ID.json
```

2. Read the helper JSON output and create the inbox directory:
   - `output_dir`: normally `data/_inbox/{paper-id}`
   - `assets_dir`: normally `data/_inbox/{paper-id}/assets`, used only if images are explicitly localized
   - final note path: `data/_inbox/{paper-id}/{MethodName}.md`
   - use `suggested_method_name` as a starting point, but correct it if the paper clearly uses a different method/model name.

3. Locate the paper source in this priority order:
   - Existing `arxiv_id`, `arxiv_url`, or `pdf_url` from the JSON.
   - If missing, search arXiv using `arxiv_search_query` from `paper_json_context.py`.
   - Then try `url`, `detail_url`, or `project_url`.
   - Stop with a clear missing-source message if no full paper, arXiv HTML/PDF, or usable project/source page can be found.

4. Read the full paper before writing:
   - Prefer arXiv HTML because it exposes figures and equations.
   - Use PDF when HTML is unavailable.
   - Check the abstract, method sections, experiments, appendix if relevant, all figures, all tables, and important formulas.
   - Use `references/cv-dl-terminology.md` only when terminology translation or naming is uncertain.

5. Write the Markdown note using `assets/paper-note-template.md`.
   - Fill YAML frontmatter with paper JSON metadata where available.
   - Fill the metadata table with authors, venue as `{Venue} {Year}`, and categories/topics from the paper JSON.
   - Use the existing dailypaper note style: Chinese technical deep reading, not a short summary.
   - Keep inline `[[概念]]` links for important technical terms, datasets, methods, simulators, losses, and architectures.
   - If no Zotero collection exists, set `zotero_collection: _inbox` or a topic-derived path from the paper JSON.

6. Use online images by default.
   - Default image strategy: online images by default.
   - 默认保留 arXiv HTML / 项目主页图片 URL, using normal Markdown image links such as `![Figure 1](https://...)`.
   - Do not run `scripts/localize_note_images.py` by default.
   - `scripts/localize_note_images.py` is an optional localization fallback only when image URLs are unreachable, the user explicitly asks for offline archiving, or the note must be migrated to an offline Obsidian vault.
   - When optional localization is needed, run:

```bash
python3 scripts/localize_note_images.py "data/_inbox/{paper-id}/{MethodName}.md"
```

   - The script stores images under the note's `assets/` directory and rewrites links as Obsidian wikilinks such as `![[assets/MethodName_fig1.png|600]]`.
   - If optional localization fails, keep the best reachable network link or explain which figure needs manual recovery.

7. Self-check the finished note.
   - Read `references/quality-standards.md` before finalizing.
   - Read `references/image-troubleshooting.md` when arXiv HTML image paths, project images, or PDF extraction are involved.
   - Use `references/concept-categories.md` to choose good concept link names; do not create concept notes or MOCs unless the user explicitly asks.

## Quality Requirements

- Include every figure from the paper. Do not include only teaser images.
- Figures may use network image URLs by default; local image files are not a completion requirement.
- Include every important formula with LaTeX, meaning, and symbol explanations.
- Include every important table with complete rows/columns or a faithful Markdown transcription.
- Explain why each figure/table/formula matters; do not paste captions as detached dumps.
- Preserve the dailypaper sections: metadata, one-sentence summary, core contributions, background, method details with formulas, figures/tables, experiments, critical thinking, and quick card.
- Use `[[概念]]` links naturally in the body. Keep them useful for Obsidian, even though this skill only writes the paper note and images.
- Never write a skeleton note in place of full reading. If the paper cannot be read completely, leave a clear failure report instead of a low-quality `.md`.

## Important Non-Goals

- Do not modify `data/papers/*.json`.
- Do not generate or validate `paper["note"]`.
- Do not call `../conference-papers/scripts/build_site.py`, `validate_notes.py`, or `resolve_links.py`.
- Do not refresh Obsidian MOCs or run git automation.
- Do not batch-read all candidates by default; process the user-specified paper unless they explicitly ask for a bounded batch.

## Bundled Resources

- `assets/paper-note-template.md`: dailypaper Obsidian note template.
- `scripts/paper_json_context.py`: normalize a paper JSON into source/output context.
- `scripts/localize_note_images.py`: optional localization fallback to download note images into inbox `assets/` and rewrite links when explicitly invoked.
- `references/quality-standards.md`: detailed figure/formula/table quality bar.
- `references/image-troubleshooting.md`: arXiv/project/PDF image fallback guidance.
- `references/concept-categories.md`: concept naming and category guidance for `[[概念]]` links.
