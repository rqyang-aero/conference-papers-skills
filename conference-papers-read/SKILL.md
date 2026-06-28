---
name: conference-papers-read
description: Use when the user asks to read selected conference papers, generate high-quality paper notes, convert draft notes into final notes, or populate structured note JSON for the conference paper website.
---

# Conference Papers Read

Use this thin entrypoint for the reading stage of the conference paper website. The site implementation lives in `../conference-papers`; high-quality paper analysis should use `paper-reader`.

## Workflow

1. Locate the target `data/papers/*.json` files.
2. For fast previews only, generate draft note data:

```bash
python3 ../conference-papers/scripts/generate_note_data.py --paper data/papers/PAPER_ID.json --draft --data data
```

3. For final notes, use `paper-reader` to read the full paper from `url`, `pdf_url`, arXiv HTML, project page, or local PDF. Check the full text, figures, tables, formulas, method sections, and experiment tables before writing.
4. Follow `../conference-papers/references/html-note-style.md`, including its Writing Style requirements, and preserve the paper-note template content before core contributions.
5. Fill `paper["note"]` with `summary`, `background`, `contributions`, `method`, `figures`, `formulas`, `experiments`, `tables`, `critical_thinking`, `related_work`, and `future_work`.
   - Set `mode` to `final` only after the full read is complete.
   - Treat final notes as deep reading articles, not summaries. Each section should connect the problem, mechanism, evidence, and judgment.
   - Write `contributions` as a non-empty list with as many bullets as the paper actually supports; do not force exactly three.
   - Write `method` as section entries aligned to the paper's method sections. Use `subsections` for paper subsections; do not flatten `3` and `3.1` as siblings.
   - Write `formulas` for important formulas. Use display math via `latex` or `\\[...\\]`; explain meaning and symbols.
   - Write `experiments` as section entries split by the paper's actual evaluation sections, such as setting, main results, ablation, generalization, efficiency, or failure cases. Use `subsections` when the paper has nested experiment sections.
   - Write `tables` for important result/ablation/config tables with the table's conclusion, not just its caption.
   - Write `critical_thinking` as exactly the required dimensions `优点`, `局限性`, and `潜在改进`, each with concrete evidence or reasoning.
   - For every figure, set `section` to one of `background`, `contributions`, `method`, `experiments`, `critical_thinking`, `related_work`, or `future_work`.
   - Use external `url` by default. Add `local_path` only if the image has been archived locally.
6. Validate final note structure before calling it done:

```bash
python3 ../conference-papers/scripts/validate_notes.py --data data
```

7. Run internal link resolution after editing notes:

```bash
python3 ../conference-papers/scripts/resolve_links.py --data data
```

## Quality Gate

Do not mark final notes complete unless all figures, tables, important formulas, critical thinking, related work, and future work have been checked against the full paper.
Reject shallow final notes. If the generated note reads like a short abstract, lacks visible formulas/tables, flattens section hierarchy, or only lists captions without explaining evidence, rewrite it before validation.
Reject structurally valid notes that still read like ad copy, literal translation, detached figure/table dumps, or generic summaries. Final notes must use the restrained Chinese technical deep-reading style defined in `html-note-style.md`.
Use `validate_notes.py` as a structural guard, but still verify content against the full paper manually.
