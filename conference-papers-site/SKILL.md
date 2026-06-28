---
name: conference-papers-site
description: Use when the user asks to build, rebuild, render, preview, or regenerate the static HTML website, topic pages, paper pages, assets, or search index from existing conference paper data.
---

# Conference Papers Site

Use this thin entrypoint for the site rendering stage. The implementation lives in `../conference-papers`; do not duplicate templates or scripts here.

## Workflow

1. Confirm the site data root, normally `data/`.
   - If not provided, `../conference-papers/config/user-config.json` supplies `site.data_dir` and `site.output_dir`.
2. Optional but recommended before rendering:

```bash
python3 ../conference-papers/scripts/resolve_links.py
```

3. Build the static site:

```bash
python3 ../conference-papers/scripts/build_site.py
```

4. Verify these outputs exist:
   - `dist/index.html`
   - `dist/search-index.json`
   - `dist/{conference}/index.html`
   - `dist/{conference}/{topic}/index.html`
   - `dist/papers/{paper-id}/index.html`

## Output

Report the built output directory and the number of papers/conferences rendered. If the user wants local preview, suggest `python3 -m http.server 8080 -d dist`.

Edit `../conference-papers/assets/site-template/paper-note.html`, `index.html`, or `collection.html` to change HTML layout.
