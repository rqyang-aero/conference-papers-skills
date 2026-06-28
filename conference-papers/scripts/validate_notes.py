#!/usr/bin/env python3
"""Validate structured paper notes before publishing the site."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

from archive_figures import is_valid_image_bytes, resolve_local_path
from conference_lib import configured_paths, load_all_papers, load_config


CONTENT_REQUIRED_SECTIONS = ("summary", "background", "contributions", "method", "experiments", "critical_thinking")
PRESENCE_REQUIRED_SECTIONS = ("related_work", "future_work")
QUALITY_FLAGS = ("all_figures_verified", "all_tables_verified", "all_formulas_verified")
CRITICAL_THINKING_DIMENSIONS = ("优点", "局限性", "潜在改进")
MIN_FINAL_NOTE_CHARS = 1000
MIN_METHOD_ENTRY_CHARS = 80
MIN_EXPERIMENT_ENTRY_CHARS = 80
MIN_CRITICAL_ENTRY_CHARS = 40


def finding(severity: str, code: str, message: str, field: str = "") -> dict:
    item = {"severity": severity, "code": code, "message": message}
    if field:
        item["field"] = field
    return item


def has_content(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return bool(value)
    return value is not None


def has_list_content(value: object) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return all(has_content(item) for item in value)


def has_titled_text_entries(value: object) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for item in value:
        if not isinstance(item, dict):
            return False
        if not str(item.get("title") or "").strip() or not str(item.get("text") or "").strip():
            return False
        subsections = item.get("subsections") or []
        if subsections and not has_titled_text_entries(subsections):
            return False
    return True


def entry_text(value: object) -> str:
    if isinstance(value, dict):
        parts = []
        for key in ("title", "text", "summary", "caption", "latex"):
            if value.get(key):
                parts.append(str(value.get(key)))
        for item in value.get("symbols") or []:
            parts.append(entry_text(item))
        for item in value.get("subsections") or []:
            parts.append(entry_text(item))
        return " ".join(parts)
    if isinstance(value, list):
        return " ".join(entry_text(item) for item in value)
    return str(value or "")


def list_text(value: object) -> str:
    if isinstance(value, list):
        return " ".join(entry_text(item) for item in value)
    return str(value or "")


def section_major(title: str) -> str:
    match = re.match(r"\s*(\d+)(?:\s|$)", title)
    return match.group(1) if match else ""


def subsection_major(title: str) -> str:
    match = re.match(r"\s*(\d+)\.\d+", title)
    return match.group(1) if match else ""


def validate_section_hierarchy(value: object, paper_id: str, field: str) -> list[dict]:
    findings = []
    if not isinstance(value, list):
        return findings
    parent_majors = {section_major(str(item.get("title") or "")) for item in value if isinstance(item, dict)}
    parent_majors.discard("")
    for item in value:
        if not isinstance(item, dict):
            continue
        major = subsection_major(str(item.get("title") or ""))
        if major and major in parent_majors:
            findings.append(
                finding(
                    "error",
                    "flattened_section_hierarchy",
                    f"{paper_id} {field} flattens section {major} and its subsection as siblings.",
                    f"note.{field}",
                )
            )
            break
        findings.extend(validate_section_hierarchy(item.get("subsections") or [], paper_id, field))
    return findings


def validate_entry_depth(value: object, paper_id: str, field: str, min_chars: int) -> list[dict]:
    findings = []
    if not isinstance(value, list):
        return findings
    for item in value:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if len(text) < min_chars:
            findings.append(
                finding(
                    "error",
                    "insufficient_note_depth",
                    f"{paper_id} {field} entry is too shallow: {item.get('title') or 'untitled'}.",
                    f"note.{field}",
                )
            )
        findings.extend(validate_entry_depth(item.get("subsections") or [], paper_id, field, min_chars))
    return findings


def has_display_formula(entry: dict) -> bool:
    latex = str(entry.get("latex") or "").strip()
    text = str(entry.get("text") or "").strip()
    return bool(latex) or "\\[" in text or "$$" in text


def validate_formula_entries(note: dict, paper_id: str) -> list[dict]:
    findings = []
    formulas = note.get("formulas") or []
    if not isinstance(formulas, list):
        findings.append(finding("error", "invalid_template_section", f"{paper_id} formulas must be a list.", "note.formulas"))
        return findings
    for formula in formulas:
        if not isinstance(formula, dict):
            findings.append(finding("error", "invalid_template_section", f"{paper_id} formula entries must be objects.", "note.formulas"))
            continue
        if not has_display_formula(formula):
            findings.append(
                finding(
                    "error",
                    "formula_not_display_math",
                    f"{paper_id} key formula must use display math via latex, \\[...\\], or $$...$$.",
                    "note.formulas",
                )
            )
    return findings


def validate_verified_evidence(note: dict, paper_id: str) -> list[dict]:
    findings = []
    quality_gate = note.get("quality_gate") or {}
    expectations = (
        ("all_tables_verified", "tables"),
        ("all_formulas_verified", "formulas"),
    )
    for flag, field in expectations:
        if quality_gate.get(flag) is True and not note.get(field):
            findings.append(
                finding(
                    "warning",
                    "missing_verified_evidence",
                    f"{paper_id} marks {flag} but note.{field} is empty.",
                    f"note.{field}",
                )
            )
    return findings


def critical_dimension_texts(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    texts = []
    for item in value:
        if isinstance(item, dict):
            texts.append(f"{item.get('title') or ''} {item.get('text') or ''}")
        else:
            texts.append(str(item))
    return texts


def validate_final_note_template(note: dict, paper_id: str) -> list[dict]:
    findings = []
    if not has_list_content(note.get("contributions")):
        findings.append(
            finding(
                "error",
                "invalid_template_section",
                f"{paper_id} final note contributions must be a non-empty list.",
                "note.contributions",
            )
        )
    if not has_titled_text_entries(note.get("method")):
        findings.append(
            finding(
                "error",
                "invalid_template_section",
                f"{paper_id} final note method must be a non-empty list of title/text entries.",
                "note.method",
            )
        )
    if not has_list_content(note.get("experiments")):
        findings.append(
            finding(
                "error",
                "invalid_template_section",
                f"{paper_id} final note experiments must be a non-empty list.",
                "note.experiments",
            )
        )
    elif isinstance(note.get("experiments"), list) and any(isinstance(item, dict) for item in note.get("experiments", [])):
        if not has_titled_text_entries(note.get("experiments")):
            findings.append(
                finding(
                    "error",
                    "invalid_template_section",
                    f"{paper_id} final note experiments must use title/text entries when structured as objects.",
                    "note.experiments",
                )
            )
    critical_texts = critical_dimension_texts(note.get("critical_thinking"))
    missing_dimensions = [dimension for dimension in CRITICAL_THINKING_DIMENSIONS if not any(dimension in text for text in critical_texts)]
    for dimension in missing_dimensions:
        findings.append(
            finding(
                "error",
                "missing_critical_dimension",
                f"{paper_id} final note critical_thinking missing {dimension}.",
                "note.critical_thinking",
            )
        )
    total_text = " ".join(
        [
            str(note.get("summary") or ""),
            str(note.get("background") or ""),
            list_text(note.get("contributions")),
            list_text(note.get("method")),
            list_text(note.get("experiments")),
            list_text(note.get("critical_thinking")),
            list_text(note.get("tables")),
            list_text(note.get("formulas")),
        ]
    )
    if len(total_text) < MIN_FINAL_NOTE_CHARS:
        findings.append(
            finding(
                "error",
                "insufficient_note_depth",
                f"{paper_id} final note is too short for a deep reading note.",
                "note",
            )
        )
    findings.extend(validate_entry_depth(note.get("method"), paper_id, "method", MIN_METHOD_ENTRY_CHARS))
    findings.extend(validate_entry_depth(note.get("experiments"), paper_id, "experiments", MIN_EXPERIMENT_ENTRY_CHARS))
    findings.extend(validate_entry_depth(note.get("critical_thinking"), paper_id, "critical_thinking", MIN_CRITICAL_ENTRY_CHARS))
    findings.extend(validate_section_hierarchy(note.get("method"), paper_id, "method"))
    findings.extend(validate_section_hierarchy(note.get("experiments"), paper_id, "experiments"))
    findings.extend(validate_formula_entries(note, paper_id))
    findings.extend(validate_verified_evidence(note, paper_id))
    return findings


def check_url_image(url: str, timeout: int = 10) -> bool:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "conference-papers-skill/0.1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("content-type", "")
            data = response.read(64)
        return is_valid_image_bytes(data, content_type)
    except Exception:
        return False


def validate_figure(figure: dict, data_dir: Path, index: int, check_urls: bool = False) -> list[dict]:
    findings = []
    label = figure.get("number") or figure.get("caption") or f"figure #{index}"
    local_path = str(figure.get("local_path") or "")
    url = str(figure.get("url") or "")
    if not local_path and not url:
        findings.append(finding("error", "figure_missing_source", f"{label} has neither local_path nor url.", "note.figures"))
        return findings
    if local_path:
        resolved = resolve_local_path(data_dir, local_path)
        if not resolved.exists():
            findings.append(finding("error", "figure_local_path_missing", f"{label} local_path does not exist: {local_path}", "note.figures"))
    elif check_urls and url and not check_url_image(url):
        findings.append(finding("error", "figure_url_unreachable", f"{label} URL is not a reachable image: {url}", "note.figures"))
    if not figure.get("caption"):
        findings.append(finding("warning", "figure_missing_caption", f"{label} has no caption.", "note.figures"))
    if not figure.get("section"):
        findings.append(finding("warning", "figure_missing_section", f"{label} has no section for inline placement.", "note.figures"))
    return findings


def validate_paper_note(paper: dict, data_dir: Path, check_urls: bool = False, strict: bool = False) -> dict:
    findings = []
    paper_id = str(paper.get("id") or paper.get("title") or "unknown")
    note = paper.get("note") or {}
    if not note:
        findings.append(finding("error", "note_missing", f"{paper_id} has no note.", "note"))
        return {"paper_id": paper_id, "ok": False, "findings": findings}
    if note.get("mode") == "draft":
        findings.append(finding("error", "note_is_draft", f"{paper_id} is still marked as draft.", "note.mode"))
    for section in CONTENT_REQUIRED_SECTIONS:
        if not has_content(note.get(section)):
            findings.append(finding("error", "missing_required_section", f"{paper_id} missing content for {section}.", f"note.{section}"))
    for section in PRESENCE_REQUIRED_SECTIONS:
        if section not in note:
            findings.append(finding("error", "missing_required_section", f"{paper_id} missing {section}.", f"note.{section}"))
    if note.get("mode") == "final":
        findings.extend(validate_final_note_template(note, paper_id))
    figures = note.get("figures") or paper.get("figures") or []
    if not figures:
        findings.append(finding("warning", "no_figures", f"{paper_id} has no figures recorded.", "note.figures"))
    for index, figure in enumerate(figures, start=1):
        findings.extend(validate_figure(figure, data_dir, index, check_urls=check_urls))
    quality_gate = note.get("quality_gate") or {}
    if quality_gate:
        for flag in QUALITY_FLAGS:
            if quality_gate.get(flag) is not True:
                findings.append(finding("warning", "quality_gate_not_verified", f"{paper_id} quality gate is not verified: {flag}.", f"note.quality_gate.{flag}"))
    else:
        findings.append(finding("warning", "quality_gate_missing", f"{paper_id} has no quality_gate for figures/tables/formulas.", "note.quality_gate"))
    has_errors = any(item["severity"] == "error" for item in findings)
    has_warnings = any(item["severity"] == "warning" for item in findings)
    return {"paper_id": paper_id, "ok": not has_errors and not (strict and has_warnings), "findings": findings}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate structured paper notes and figure references.")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--config", type=Path, help="Optional config JSON override.")
    parser.add_argument("--check-urls", action="store_true", help="Check external figure URLs for reachable image responses.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as validation failures.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    config = load_config(skill_dir, site_dir=Path.cwd(), config_path=args.config)
    default_data, _ = configured_paths(config)
    data_dir = args.data or default_data
    results = [validate_paper_note(paper, data_dir=data_dir, check_urls=args.check_urls, strict=args.strict) for paper in load_all_papers(data_dir)]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for result in results:
            for item in result["findings"]:
                print(f"{item['severity'].upper()} {result['paper_id']} {item['code']}: {item['message']}")
        failures = [result for result in results if not result["ok"]]
        print(f"validated {len(results)} papers, {len(failures)} failed")
    raise SystemExit(1 if any(not result["ok"] for result in results) else 0)


if __name__ == "__main__":
    main()
