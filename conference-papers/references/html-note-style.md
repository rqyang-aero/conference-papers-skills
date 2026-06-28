# HTML Note Style

Final notes are structured paper-reading notes rendered as HTML. Draft notes are allowed for preview, but must remain visibly marked as draft via `note.mode = "draft"` and `quality_gate.requires_full_read = true`.

## Writing Style

Write final notes as restrained Chinese technical deep-reading articles for embodied AI, robotics, and computer vision readers. Keep the readable pacing of a strong public technical article, but let paper evidence set the ceiling for every claim.

- Open with the paper's real pain point, why it matters, the core mechanism, and the strongest evidence.
- Write `background` as task challenge → prior-method weakness → this paper's entry point. Avoid generic field introductions.
- Write `contributions` from the paper's actual claims and supporting evidence, not from marketing phrasing.
- Write `method` as module role → inputs/outputs → key mechanism → formula/figure/table support → design meaning. Do not merely list module names.
- Write `experiments` as setup → metrics → main result → ablation/generalization/efficiency → conclusion boundary. State what the evidence proves and what it does not prove.
- Write `critical_thinking` with concrete assumptions, data scope, compute/deployment cost, evaluation limits, or failure cases. Do not use vague lines such as "future work can improve robustness."
- Use vivid but controlled wording. Avoid unsupported exaggerations such as "revolutionary", "completely solves", "perfect", or "全面碾压"; if the paper directly supports a strong claim, still phrase it with the exact metric and scope.
- Do not let the note read like an abstract, ad copy, a literal translation, or a detached dump of figures and tables.

## Final Note Template

Use the fixed outer fields below for every final note. Keep the inner bullets paper-specific; do not force a fixed number of contributions, method blocks, or experiment blocks. Final notes should read like deep paper-reading articles, not short abstracts.

```json
{
  "mode": "final",
  "summary": "One-sentence reading takeaway: problem, method, and why it matters.",
  "background": "...",
  "contributions": [
    "Contribution written from the paper's actual claims and evidence."
  ],
  "method": [
    {
      "title": "3 Method section title from the paper",
      "text": "Explain the parent section's role: inputs, outputs, modules, objective, and why this design matters.",
      "subsections": [
        {
          "title": "3.1 Subsection title from the paper",
          "text": "Explain the mechanism, why it is needed, and which formula/figure/table supports it."
        }
      ]
    }
  ],
  "figures": [],
  "formulas": [
    {
      "title": "Formula name or equation number",
      "latex": "p(a_t | o_t, g_t)",
      "text": "Explain what this display equation means and why it is important.",
      "symbols": [
        {"symbol": "a_t", "text": "action at time t"}
      ],
      "section": "method"
    }
  ],
  "experiments": [
    {
      "title": "5 Experiments",
      "text": "Explain the evaluation setup, datasets/tasks, baselines, and metrics.",
      "subsections": [
        {
          "title": "5.2 Main Results",
          "text": "Explain what was measured, which table/figure proves it, and what the result does not prove."
        }
      ]
    }
  ],
  "tables": [
    {
      "title": "Table 1",
      "text": "Describe the table content.",
      "summary": "State the conclusion the table supports.",
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
```

Final-note structure rules enforced by `validate_notes.py`:

- `contributions` must be a non-empty list. Use as many bullets as the paper actually supports.
- `method` must be a non-empty list of section entries. Use `subsections` for paper subsections; do not flatten `3` and `3.1` as siblings.
- `formulas` should include important formulas as display math via `latex`, `\\[...\\]`, or `$$...$$`. Explain meaning and symbols.
- `experiments` must be a non-empty list split by the paper's actual experimental sections, such as setting, main results, ablations, generalization, efficiency, or failure cases. Use `subsections` for nested experiment sections.
- `tables` should include important result, ablation, or configuration tables with a conclusion, not just a caption.
- `critical_thinking` must include the three dimensions `优点`, `局限性`, and `潜在改进`.
- Important formulas must be display math. Inline `\\(...\\)` is allowed only for minor symbols in prose.
- Final notes must clear the depth guard in `validate_notes.py`: shallow method/experiment/critical entries, flattened section hierarchy, or missing visible formula/table evidence are publish blockers.

## Required Section Order

1. Metadata and summary from the paper template before core contributions.
2. Research background.
3. Main contributions.
4. Method.
5. Figures placed near the relevant method or experiment discussion.
6. Key formulas.
7. Experiments.
8. Key tables.
9. Critical thinking.
10. Related work.
11. Future work.

## Figure Synchronization

Before finalizing a note:

- Count all figures in arXiv HTML, project page, or PDF extraction.
- Include every figure in `note.figures`.
- Keep captions faithful to the paper.
- Place architecture/method figures in the method section and result/ablation figures in the experiment section when writing the narrative.
- Do not invent image URLs. Use original URLs or downloaded local paths.

Figures do not need to be downloaded for synchronization. The renderer uses `section` metadata to place each figure near the matching note section. Use external `url` by default and `local_path` only when archiving important papers.

For important papers or unstable image hosts, archive external figures after the note has figure URLs:

```bash
python3 scripts/archive_figures.py --data data
```

```json
{
  "number": "Figure 1",
  "url": "https://arxiv.org/html/xxxx/figures/overview.png",
  "caption": "Overview of the method.",
  "section": "method",
  "anchor": "method-overview"
}
```

Supported `section` values:

- `background`
- `contributions`
- `method`
- `experiments`
- `critical_thinking`
- `related_work`
- `future_work`

Figures without `section` are rendered in the final unmatched Figures block.

## Critical Reading Requirements

Write specific judgments:

- What problem is solved and why prior methods are insufficient.
- What is the actual method, including inputs, outputs, training objective, core modules, and necessary formulas.
- How each method section maps to the paper's own sections and subsections without flattening hierarchy.
- What experiments prove, and what they do not prove; split experiments according to the paper's actual evaluation structure.
- What each important table or formula contributes to the argument.
- Whether assumptions, evaluation scope, data requirements, compute cost, or sim-to-real claims are weak.
- What the paper's strengths, limitations, and potential improvements are.
- How the paper relates to stored papers; use `related_work` and `future_work` entries with titles that `resolve_links.py` can match.

## Related/Future Work Entry Format

```json
{
  "title": "OpenVLA",
  "text": "Used as the closest VLA policy baseline for comparison."
}
```

After writing related/future entries, run:

```bash
python3 scripts/validate_notes.py --data data
python3 scripts/resolve_links.py --data data
```

`validate_notes.py` checks structure, draft status, figure references, and quality gate flags. It does not replace checking the note against the full paper.
