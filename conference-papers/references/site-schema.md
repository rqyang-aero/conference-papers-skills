# Site Schema

The site uses editable JSON files and static HTML output. Keep the schema stable so users can patch data by hand.

## Data Layout

```text
data/
  assets/papers/{paper-id}/figure.png
  conferences/{conference-slug}-{year}.json
  papers/{paper-id}.json
config/
  user-config.local.json
dist/
  assets/papers/{paper-id}/figure.png
  index.html
  {conference}/index.html
  {conference}/{topic}/index.html
  papers/{paper-id}/index.html
  search-index.json
```

## Paper Object

```json
{
  "id": "stable-paper-id",
  "title": "Paper title",
  "conference": "CVPR",
  "year": 2026,
  "topics": ["VLA", "Humanoid"],
  "authors": ["A. Author"],
  "abstract": "Abstract text",
  "url": "https://...",
  "detail_url": "https://...",
  "pdf_url": "https://...",
  "arxiv_id": "2601.00001",
  "arxiv_url": "https://arxiv.org/abs/2601.00001",
  "arxiv_match_score": 0.97,
  "project_url": "https://...",
  "source": "cvf|rss|manual",
  "source_url": "https://source",
  "figures": [
    {
      "number": "Figure 1",
      "url": "https://...",
      "local_path": "",
      "caption": "Caption text",
      "section": "method",
      "anchor": "method-overview"
    }
  ],
  "note": {
    "mode": "final",
    "summary": "...",
    "background": "...",
    "contributions": ["..."],
    "method": [
      {
        "title": "3 Method section title",
        "text": "Parent method section explanation.",
        "subsections": [
          {
            "title": "3.1 Method subsection title",
            "text": "Subsection mechanism, evidence, and why it matters."
          }
        ]
      }
    ],
    "figures": [],
    "formulas": [
      {
        "title": "Formula name",
        "latex": "J(\\theta)=\\mathbb{E}_{\\tau}[r(\\tau)]",
        "text": "Formula meaning and why it matters.",
        "symbols": [
          {"symbol": "\\theta", "text": "policy parameters"}
        ],
        "section": "method"
      }
    ],
    "experiments": [
      {
        "title": "5 Experiments",
        "text": "Evaluation setup, baselines, metrics, and tasks.",
        "subsections": [
          {
            "title": "5.2 Main Results",
            "text": "Main result interpretation and what it proves."
          }
        ]
      }
    ],
    "tables": [
      {
        "title": "Table 1",
        "text": "Table content or caption.",
        "summary": "Conclusion supported by this table.",
        "section": "experiments"
      }
    ],
    "critical_thinking": [
      {"title": "优点", "text": "..."},
      {"title": "局限性", "text": "..."},
      {"title": "潜在改进", "text": "..."}
    ],
    "related_work": [],
    "future_work": [],
    "quality_gate": {
      "all_figures_verified": true,
      "all_tables_verified": true,
      "all_formulas_verified": true
    }
  }
}
```

## Link Resolution

`related_work` and `future_work` entries may omit `paper_id`. `scripts/resolve_links.py` matches by title or title prefix and adds:

```json
{
  "title": "OpenVLA",
  "text": "Baseline policy.",
  "paper_id": "openvla-an-open-vision-language-action-model",
  "href": "../../papers/openvla-an-open-vision-language-action-model/"
}
```

## Search Index

`dist/search-index.json` contains title, authors, conference, year, topics, abstract, and page URL. The browser-side search script performs simple case-insensitive substring matching across those fields.

## Templates

The renderer uses editable HTML fragments from `assets/site-template/`:

- `paper-note.html` for single paper note pages.
- `index.html` for the home page.
- `collection.html` for conference and topic pages.

## Figure Placement

The site renderer places figures inline by `figure.section`. External URLs are valid and are used directly in `<img src="...">`; `local_path` is optional and takes precedence when present. `scripts/archive_figures.py` stores local images under `data/assets/papers/{paper-id}/` and writes page-relative paths such as `../../assets/papers/{paper-id}/figure-1.png`. `build_site.py` copies `data/assets/` into `dist/assets/`.

Known section values are `background`, `contributions`, `method`, `experiments`, `critical_thinking`, `related_work`, and `future_work`. Figures without a known section are rendered in the final Figures block of the paper page.
