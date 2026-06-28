#!/usr/bin/env python3
"""Shared helpers for the conference-papers skill.

The module intentionally uses only Python's standard library so the skill can
run in fresh Codex workspaces without npm or pip setup.
"""

from __future__ import annotations

import copy
import hashlib
import html
import json
import re
import shutil
import textwrap
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Iterable


TOPIC_KEYWORDS = {
    "vla": [
        "vla",
        "vision language action",
        "vision-language-action",
        "vision-language action",
        "language-conditioned policy",
        "language conditioned policy",
    ],
    "humanoid": ["humanoid", "whole-body", "whole body", "biped", "legged robot"],
    "locomotion": ["locomotion", "locomotor", "walking", "gait", "legged"],
    "loco-manipulation": ["loco-manipulation", "loco manipulation", "mobile manipulation"],
}


DEFAULT_CONFIG = {
    "site": {
        "title": "Conference Papers",
        "data_dir": "data",
        "output_dir": "dist",
    },
    "defaults": {
        "conference": "CVPR",
        "year": 2026,
        "topics": ["VLA", "Humanoid", "locomotion", "loco-manipulation"],
    },
    "sources": [],
    "topic_keywords": TOPIC_KEYWORDS,
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path, default: object | None = None) -> object:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config(skill_dir: Path | None = None, site_dir: Path | None = None, config_path: Path | None = None) -> dict:
    """Load base config plus optional local overrides.

    Precedence, lowest to highest:
    built-in defaults -> skill config/user-config.json ->
    skill config/user-config.local.json -> site config/user-config.local.json.
    """
    if skill_dir is None:
        skill_dir = Path(__file__).resolve().parents[1]
    config = copy.deepcopy(DEFAULT_CONFIG)
    candidates: list[Path] = []
    if config_path:
        candidates.append(config_path)
    else:
        candidates.append(skill_dir / "config" / "user-config.json")
    candidates.append(skill_dir / "config" / "user-config.local.json")
    if site_dir:
        candidates.append(site_dir / "config" / "user-config.local.json")

    for candidate in candidates:
        if candidate.exists():
            loaded = load_json(candidate, default={})
            if isinstance(loaded, dict):
                config = deep_merge(config, loaded)
    apply_topic_keywords(config)
    return config


def apply_topic_keywords(config: dict) -> None:
    configured = config.get("topic_keywords") or {}
    if not isinstance(configured, dict):
        return
    for topic, needles in configured.items():
        if isinstance(needles, list):
            TOPIC_KEYWORDS[str(topic).lower()] = [str(item) for item in needles]


def configured_defaults(config: dict) -> tuple[str, int, list[str]]:
    defaults = config.get("defaults", {})
    conference = str(defaults.get("conference") or "CVPR")
    year = int(defaults.get("year") or datetime.utcnow().year)
    topics = [str(topic) for topic in defaults.get("topics", [])]
    return conference, year, topics


def configured_paths(config: dict) -> tuple[Path, Path]:
    site = config.get("site", {})
    return Path(site.get("data_dir") or "data"), Path(site.get("output_dir") or "dist")


def find_config_source(config: dict, conference: str, year: int, source_name: str = "") -> dict | None:
    sources = config.get("sources") or []
    for source in sources:
        if not isinstance(source, dict):
            continue
        if source_name and source.get("name") != source_name:
            continue
        source_conference = str(source.get("conference") or conference)
        source_year = int(source.get("year") or year)
        if source_conference.lower() == conference.lower() and source_year == int(year):
            return source
    return sources[0] if sources and isinstance(sources[0], dict) and not source_name else None


def fetch_text(url_or_path: str, timeout: int = 45) -> str:
    parsed = urllib.parse.urlparse(url_or_path)
    if parsed.scheme in ("http", "https"):
        req = urllib.request.Request(url_or_path, headers={"User-Agent": "conference-papers-skill/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    if parsed.scheme == "file":
        return Path(urllib.request.url2pathname(parsed.path)).read_text(encoding="utf-8")
    return Path(url_or_path).read_text(encoding="utf-8")


def strip_tags(value: str) -> str:
    value = re.sub(r"<(br|p|div|li|dt|dd|h\d)\b[^>]*>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def attr_value(tag: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*=\s*(['\"])(.*?)\1", tag, flags=re.I | re.S)
    return html.unescape(match.group(2).strip()) if match else ""


def slugify(value: str, max_len: int = 90) -> str:
    value = html.unescape(value).lower()
    value = value.replace("π", "pi").replace("μ", "mu")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    value = re.sub(r"-{2,}", "-", value)
    if not value:
        value = "paper"
    return value[:max_len].strip("-")


def compact_title(value: str) -> str:
    value = strip_tags(value).lower()
    value = re.sub(r"[:：].*$", "", value)
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value


def paper_id_for(title: str, url: str = "", conference: str = "", year: int | str = "") -> str:
    base = slugify(title)
    if len(base) >= 12:
        return base
    digest = hashlib.sha1(f"{conference}:{year}:{title}:{url}".encode("utf-8")).hexdigest()[:8]
    return f"{base}-{digest}"


def split_authors(value: str | list[str] | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    value = strip_tags(value)
    paren = re.search(r"\(([^)]+)\)", value)
    if paren and "@" in value:
        value = paren.group(1)
    pieces = re.split(r"\s*(?:,|;|\band\b)\s*", value)
    return [p.strip() for p in pieces if p.strip() and "@" not in p]


def unique_ordered(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def topic_needles(topic: str) -> list[str]:
    key = topic.lower()
    needles = [key, key.replace("-", " "), key.replace(" ", "-")]
    needles.extend(TOPIC_KEYWORDS.get(key, []))
    return unique_ordered(needles)


def classify_topics(paper: dict, topics: Iterable[str]) -> list[str]:
    text = " ".join(
        str(paper.get(field, ""))
        for field in ("title", "abstract", "summary", "keywords", "method_summary")
    ).lower()
    hits: list[str] = []
    for topic in topics:
        if any(needle.lower() in text for needle in topic_needles(topic)):
            hits.append(topic)
    return unique_ordered(hits)


def normalize_paper(
    raw: dict,
    conference: str,
    year: int,
    topics: Iterable[str] = (),
    source: str = "manual",
    source_url: str = "",
) -> dict:
    title = strip_tags(str(raw.get("title", "")))
    url = raw.get("url") or raw.get("detail_url") or raw.get("paper_url") or ""
    pdf_url = raw.get("pdf_url") or raw.get("pdf") or ""
    paper = {
        "id": raw.get("id") or paper_id_for(title, str(url), conference, year),
        "title": title,
        "conference": conference,
        "year": int(year),
        "topics": [],
        "authors": split_authors(raw.get("authors")),
        "abstract": strip_tags(str(raw.get("abstract") or raw.get("summary") or "")),
        "url": str(url),
        "detail_url": str(raw.get("detail_url") or raw.get("url") or ""),
        "pdf_url": str(pdf_url),
        "project_url": str(raw.get("project_url") or ""),
        "source": raw.get("source") or source,
        "source_url": raw.get("source_url") or source_url,
        "figures": raw.get("figures") or [],
        "note": raw.get("note") or {},
        "created_at": raw.get("created_at") or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    explicit_topics = unique_ordered(list(raw.get("topics") or []) + list(topics))
    inferred_topics = classify_topics(paper, explicit_topics)
    paper["topics"] = unique_ordered(inferred_topics or explicit_topics)
    return paper


def merge_paper(existing: dict | None, incoming: dict) -> dict:
    if not existing:
        return incoming
    merged = copy.deepcopy(existing)
    for key, value in incoming.items():
        if key == "topics":
            merged[key] = sorted(unique_ordered(list(existing.get(key, [])) + list(value or [])), key=str.lower)
        elif key == "authors":
            merged[key] = unique_ordered(list(existing.get(key, [])) + list(value or []))
        elif key == "figures":
            seen = {str(fig.get("url") or fig.get("local_path") or fig.get("caption")) for fig in existing.get("figures", [])}
            merged_figs = list(existing.get("figures", []))
            for fig in value or []:
                fig_key = str(fig.get("url") or fig.get("local_path") or fig.get("caption"))
                if fig_key and fig_key not in seen:
                    merged_figs.append(fig)
                    seen.add(fig_key)
            merged[key] = merged_figs
        elif key == "note":
            note = copy.deepcopy(existing.get("note") or {})
            for note_key, note_value in (value or {}).items():
                if note_value and not note.get(note_key):
                    note[note_key] = note_value
            merged[key] = note
        elif value and not merged.get(key):
            merged[key] = value
    merged["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    return merged


def extract_links(block: str, base_url: str) -> list[tuple[str, str]]:
    links = []
    for match in re.finditer(r"<a\b([^>]*)>(.*?)</a>", block, flags=re.I | re.S):
        href = attr_value(match.group(1), "href")
        if href:
            links.append((urllib.parse.urljoin(base_url, href), strip_tags(match.group(2))))
    for match in re.finditer(r"<form\b([^>]*)>", block, flags=re.I | re.S):
        action = attr_value(match.group(1), "action")
        if action:
            links.append((urllib.parse.urljoin(base_url, action), "detail"))
    return links


def first_pdf_url(block: str, base_url: str) -> str:
    for href, label in extract_links(block, base_url):
        if ".pdf" in href.lower() or "pdf" in label.lower():
            return href
    return ""


def first_detail_url(block: str, base_url: str) -> str:
    for href, label in extract_links(block, base_url):
        low = href.lower()
        if ".pdf" not in low and not any(skip in low for skip in ("javascript:", "mailto:")):
            return href
    return ""


def extract_class_text(block: str, class_name: str) -> str:
    pattern = rf"<[^>]*class\s*=\s*['\"][^'\"]*\b{re.escape(class_name)}\b[^'\"]*['\"][^>]*>(.*?)</[^>]+>"
    match = re.search(pattern, block, flags=re.I | re.S)
    return strip_tags(match.group(1)) if match else ""


def parse_cvf_html(html_text: str, base_url: str, conference: str, year: int, topics: Iterable[str]) -> list[dict]:
    papers: list[dict] = []
    seen_titles = set()

    card_blocks = re.findall(
        r"(<div\b[^>]*class\s*=\s*['\"][^'\"]*(?:paper-card|paper|card)[^'\"]*['\"][^>]*>.*?)(?=<div\b[^>]*class\s*=\s*['\"][^'\"]*(?:paper-card|paper|card)\b|<dt\b[^>]*class\s*=\s*['\"][^'\"]*ptitle|</body>|</html>|$)",
        html_text,
        flags=re.I | re.S,
    )
    legacy_blocks = [
        dt + dd
        for dt, dd in re.findall(
            r"(<dt\b[^>]*class\s*=\s*['\"][^'\"]*ptitle[^'\"]*['\"][^>]*>.*?</dt>)\s*(<dd\b.*?</dd>)",
            html_text,
            flags=re.I | re.S,
        )
    ]
    blocks = card_blocks + legacy_blocks
    if not blocks:
        blocks = re.findall(r"<li\b[^>]*>.*?</li>", html_text, flags=re.I | re.S)

    for block in blocks:
        title = extract_class_text(block, "paper-title") or extract_class_text(block, "ptitle")
        if not title:
            title_match = re.search(r"<a\b[^>]*>(.*?)</a>", block, flags=re.I | re.S)
            title = strip_tags(title_match.group(1)) if title_match else ""
        title = re.sub(r"^(paper|poster|oral)\s*[:#-]?\s*", "", title, flags=re.I).strip()
        if not title or len(title) < 8:
            continue
        title_key = title.lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        authors = extract_class_text(block, "authors") or extract_class_text(block, "author")
        raw = {
            "title": title,
            "authors": split_authors(authors),
            "abstract": extract_class_text(block, "abstract"),
            "detail_url": first_detail_url(block, base_url),
            "pdf_url": first_pdf_url(block, base_url),
        }
        papers.append(normalize_paper(raw, conference, year, topics, source="cvf", source_url=base_url))
    return papers


def xml_text(element: ET.Element, names: Iterable[str]) -> str:
    for name in names:
        found = element.find(name)
        if found is not None and found.text:
            return strip_tags(found.text)
    return ""


def strip_xml_namespaces(root: ET.Element) -> ET.Element:
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def parse_rss(xml_text_value: str, source_url: str, conference: str, year: int, topics: Iterable[str]) -> list[dict]:
    root = strip_xml_namespaces(ET.fromstring(xml_text_value))
    items = root.findall(".//item") or root.findall(".//entry")
    papers = []
    for item in items:
        title = xml_text(item, ["title"])
        link = xml_text(item, ["link"])
        if not link:
            link_el = item.find("link")
            link = link_el.attrib.get("href", "") if link_el is not None else ""
        summary = xml_text(item, ["description", "summary", "content"])
        author = xml_text(item, ["author", "creator"])
        if not author:
            author_name = item.find("author/name")
            author = author_name.text if author_name is not None and author_name.text else ""
        raw = {
            "title": title,
            "url": link,
            "authors": split_authors(author),
            "abstract": summary,
        }
        papers.append(normalize_paper(raw, conference, year, topics, source="rss", source_url=source_url))
    return [p for p in papers if p.get("title")]


def parse_manual_json(text: str, conference: str, year: int, topics: Iterable[str], source_url: str = "") -> list[dict]:
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("papers", [])
    return [normalize_paper(item, conference, year, topics, source="manual", source_url=source_url) for item in data]


def parse_source_text(text: str, source_url: str, conference: str, year: int, topics: Iterable[str]) -> list[dict]:
    stripped = text.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        return parse_manual_json(text, conference, year, topics, source_url=source_url)
    if "<rss" in stripped[:200].lower() or "<feed" in stripped[:200].lower():
        return parse_rss(text, source_url, conference, year, topics)
    return parse_cvf_html(text, source_url, conference, year, topics)


def data_paths(data_dir: Path) -> dict[str, Path]:
    return {
        "root": data_dir,
        "papers": data_dir / "papers",
        "conferences": data_dir / "conferences",
    }


def load_all_papers(data_dir: Path) -> list[dict]:
    paper_dir = data_paths(data_dir)["papers"]
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(paper_dir.glob("*.json"))] if paper_dir.exists() else []


def paper_path(data_dir: Path, paper_id: str) -> Path:
    return data_paths(data_dir)["papers"] / f"{paper_id}.json"


def find_existing_paper(data_dir: Path, incoming: dict) -> dict | None:
    incoming_title = compact_title(incoming.get("title", ""))
    for paper in load_all_papers(data_dir):
        if paper.get("id") == incoming.get("id") or compact_title(paper.get("title", "")) == incoming_title:
            return paper
    return None


def save_paper(data_dir: Path, incoming: dict) -> dict:
    existing = find_existing_paper(data_dir, incoming)
    merged = merge_paper(existing, incoming)
    write_json(paper_path(data_dir, merged["id"]), merged)
    if existing and existing.get("id") != merged["id"]:
        old_path = paper_path(data_dir, existing["id"])
        if old_path.exists():
            old_path.unlink()
    return merged


def conference_index_path(data_dir: Path, conference: str, year: int) -> Path:
    return data_paths(data_dir)["conferences"] / f"{slugify(conference)}-{year}.json"


def update_conference_index(data_dir: Path, conference: str, year: int, papers: Iterable[dict], source_url: str = "") -> dict:
    path = conference_index_path(data_dir, conference, year)
    current = load_json(path, default={}) or {}
    indexed = {item["id"]: item for item in current.get("papers", [])}
    for paper in papers:
        indexed[paper["id"]] = {
            "id": paper["id"],
            "title": paper["title"],
            "topics": paper.get("topics", []),
        }
    index = {
        "conference": conference,
        "year": int(year),
        "source_url": source_url or current.get("source_url", ""),
        "papers": sorted(indexed.values(), key=lambda item: item["title"].lower()),
        "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    write_json(path, index)
    return index


def generate_draft_note(paper: dict) -> dict:
    title = paper.get("title", "Untitled")
    abstract = paper.get("abstract", "")
    figures = paper.get("figures", [])
    contribution = abstract or f"{title} needs a full Codex/paper-reader pass before this note is considered complete."
    return {
        "mode": "draft",
        "summary": first_sentence(abstract) or f"Draft note for {title}.",
        "background": abstract or "Draft placeholder: read the full paper to complete the research background.",
        "contributions": [contribution],
        "method": "Draft placeholder: extract architecture, inputs/outputs, training objective, and implementation details from the full paper.",
        "experiments": "Draft placeholder: extract datasets, metrics, baselines, ablations, and real-world or simulation setup from the full paper.",
        "figures": figures,
        "critical_thinking": "Draft placeholder: assess assumptions, evidence strength, evaluation gaps, reproducibility, and engineering cost.",
        "related_work": [],
        "future_work": [],
        "quality_gate": {
            "requires_full_read": True,
            "all_figures_verified": bool(figures),
            "all_tables_verified": False,
            "all_formulas_verified": False,
        },
    }


def first_sentence(text: str) -> str:
    match = re.search(r"(.+?[.!?])(?:\s|$)", text.strip())
    return match.group(1).strip() if match else textwrap.shorten(text.strip(), width=160, placeholder="...")


def extract_figures_from_html(html_text: str, base_url: str) -> list[dict]:
    figures = []
    for idx, match in enumerate(re.finditer(r"<figure\b[^>]*>(.*?)</figure>", html_text, flags=re.I | re.S), start=1):
        block = match.group(1)
        img = re.search(r"<img\b([^>]*)>", block, flags=re.I | re.S)
        if not img:
            continue
        src = attr_value(img.group(1), "src")
        caption = ""
        cap = re.search(r"<figcaption\b[^>]*>(.*?)</figcaption>", block, flags=re.I | re.S)
        if cap:
            caption = strip_tags(cap.group(1))
        figures.append(
            {
                "number": f"Figure {idx}",
                "url": urllib.parse.urljoin(base_url, src),
                "caption": caption,
                "section": infer_figure_section(caption),
                "anchor": slugify(caption or f"figure-{idx}", max_len=48),
            }
        )
    return figures


def infer_figure_section(caption: str) -> str:
    text = caption.lower()
    if any(word in text for word in ("overview", "framework", "architecture", "pipeline", "method", "model", "module", "policy")):
        return "method"
    if any(word in text for word in ("result", "comparison", "ablation", "benchmark", "experiment", "success rate", "metric", "evaluation")):
        return "experiments"
    if any(word in text for word in ("motivation", "problem", "background", "dataset", "task setup")):
        return "background"
    return ""


def extract_project_urls(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s\"'<>)]*(?:github\.io|github\.com|project|demo|page)[^\s\"'<>)]*", text, flags=re.I)
    return unique_ordered(urls)


def resolve_internal_links(note: dict, papers: list[dict]) -> dict:
    resolved = copy.deepcopy(note or {})
    title_map = {}
    for paper in papers:
        title = paper.get("title", "")
        if not title:
            continue
        title_map[compact_title(title)] = paper
        short = compact_title(re.sub(r"[:：].*$", "", title))
        if short:
            title_map[short] = paper

    for section in ("related_work", "future_work"):
        entries = resolved.get(section) or []
        fixed_entries = []
        for entry in entries:
            item = {"title": str(entry), "text": ""} if isinstance(entry, str) else copy.deepcopy(entry)
            key = compact_title(item.get("title") or item.get("text") or "")
            match = title_map.get(key)
            if not match and key:
                for candidate_key, candidate in title_map.items():
                    if key in candidate_key or candidate_key in key:
                        match = candidate
                        break
            if match:
                item["paper_id"] = match["id"]
                item["href"] = f"../../papers/{match['id']}/"
            fixed_entries.append(item)
        resolved[section] = fixed_entries
    return resolved


def html_escape(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def page(title: str, body: str, prefix: str = "") -> str:
    return page_with_title(title, body, prefix=prefix, site_title="Conference Papers")


def page_with_title(title: str, body: str, prefix: str = "", site_title: str = "Conference Papers") -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html_escape(title)}</title>
  <link rel="stylesheet" href="{prefix}assets/site.css">
  <script>window.SEARCH_INDEX_PATH = "{prefix}search-index.json";</script>
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [["\\\\(", "\\\\)"]],
        displayMath: [["\\\\[", "\\\\]"]]
      }}
    }};
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
  <header class="topbar">
    <a class="brand" href="{prefix}index.html">{html_escape(site_title)}</a>
    <label class="search"><span>Search</span><input id="site-search" type="search" placeholder="title, author, topic"></label>
  </header>
  <main class="layout">
    <aside id="search-results" class="sidebar"></aside>
    <section class="content">{body}</section>
  </main>
  <script src="{prefix}assets/search.js"></script>
</body>
</html>
"""


def render_template(skill_dir: Path, template_name: str, context: dict[str, object]) -> str:
    template_path = skill_dir / "assets" / "site-template" / template_name
    template = template_path.read_text(encoding="utf-8")
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    rendered = re.sub(r"\{\{[a-zA-Z0-9_]+\}\}", "", rendered)
    return rendered


def render_paper_list(papers: Iterable[dict], prefix: str = "") -> str:
    items = []
    for paper in sorted(papers, key=lambda p: p.get("title", "").lower()):
        topics = " ".join(f"<span class=\"chip\">{html_escape(t)}</span>" for t in paper.get("topics", []))
        authors = ", ".join(paper.get("authors", []))
        items.append(
            f"""<article class="paper-row">
  <h3><a href="{prefix}papers/{paper['id']}/">{html_escape(paper.get('title'))}</a></h3>
  <p class="meta">{html_escape(paper.get('conference'))} {html_escape(paper.get('year'))} · {html_escape(authors)}</p>
  <p>{html_escape(first_sentence(paper.get('abstract', '')))}</p>
  <div class="chips">{topics}</div>
</article>"""
        )
    return "\n".join(items) if items else "<p>No papers yet.</p>"


def render_note_entries(entries: Iterable[object], child: bool = False) -> str:
    blocks = []
    for item in entries or []:
        if not isinstance(item, dict):
            blocks.append(f"<li>{html_escape(item)}</li>")
            continue
        title = item.get("title") or item.get("number") or item.get("text") or ""
        text = item.get("text") or item.get("caption") or item.get("summary") or ""
        heading = "h4" if child else "h3"
        css_class = "note-subentry" if child else "note-entry"
        if item.get("paper_id"):
            label = f"<a href=\"../../papers/{html_escape(item['paper_id'])}/\">{html_escape(title)}</a>"
        else:
            label = html_escape(title)
        parts = [f"<{heading}>{label}</{heading}>"]
        if text:
            parts.append(f"<p>{html_escape(text)}</p>")
        subsections = item.get("subsections") or []
        if isinstance(subsections, list) and subsections:
            parts.append(render_note_entries(subsections, child=True))
        blocks.append(f"<section class=\"{css_class}\">{''.join(parts)}</section>")
    return "".join(blocks)


def should_render_structured(value: object) -> bool:
    if not isinstance(value, list):
        return False
    return any(isinstance(item, dict) and ("subsections" in item or "title" in item) for item in value)


def render_note_section(title: str, value: object, structured: bool = False) -> str:
    if not value:
        return ""
    if structured and should_render_structured(value):
        rendered = f"<div class=\"note-entries\">{render_note_entries(value)}</div>"
    elif isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                label = item.get("title") or item.get("number") or item.get("text") or ""
                text = item.get("text") or item.get("caption") or item.get("summary") or ""
                if item.get("paper_id"):
                    label = f"<a href=\"../../papers/{html_escape(item['paper_id'])}/\">{html_escape(label)}</a>"
                else:
                    label = html_escape(label)
                parts.append(f"<li><strong>{label}</strong>{': ' + html_escape(text) if text else ''}</li>")
            else:
                parts.append(f"<li>{html_escape(item)}</li>")
        rendered = f"<ul>{''.join(parts)}</ul>"
    else:
        rendered = f"<p>{html_escape(value)}</p>"
    return f"<h2>{html_escape(title)}</h2>{rendered}"


def render_figures(figures: Iterable[dict], heading: str = "Figures") -> str:
    blocks = []
    for fig in figures or []:
        src = fig.get("local_path") or fig.get("url")
        if not src:
            continue
        caption = fig.get("caption") or fig.get("number") or "Figure"
        figure_id = fig.get("anchor") or slugify(caption, max_len=48)
        number = fig.get("number") or ""
        blocks.append(
            f"""<figure id="{html_escape(figure_id)}">
  <img src="{html_escape(src)}" alt="{html_escape(caption)}">
  <figcaption>{html_escape(number + ': ' if number else '')}{html_escape(caption)}</figcaption>
</figure>"""
        )
    return f"<h2>{html_escape(heading)}</h2>" + "\n".join(blocks) if blocks else ""


def normalize_section_name(value: str) -> str:
    if not value or not value.strip():
        return ""
    text = slugify(value)
    aliases = {
        "research-background": "background",
        "background": "background",
        "motivation": "background",
        "main-contributions": "contributions",
        "contributions": "contributions",
        "contribution": "contributions",
        "method": "method",
        "methods": "method",
        "approach": "method",
        "architecture": "method",
        "experiment": "experiments",
        "experiments": "experiments",
        "results": "experiments",
        "evaluation": "experiments",
        "critical-thinking": "critical_thinking",
        "critique": "critical_thinking",
        "related-work": "related_work",
        "future-work": "future_work",
    }
    return aliases.get(text, text.replace("-", "_"))


def split_figures_by_section(figures: Iterable[dict]) -> tuple[dict[str, list[dict]], list[dict]]:
    grouped: dict[str, list[dict]] = {}
    unmatched: list[dict] = []
    for fig in figures or []:
        section = normalize_section_name(str(fig.get("section") or ""))
        if section:
            grouped.setdefault(section, []).append(fig)
        else:
            unmatched.append(fig)
    return grouped, unmatched


def render_note_section_with_figures(title: str, value: object, figures: Iterable[dict] = (), structured: bool = False) -> str:
    section = render_note_section(title, value, structured=structured)
    figure_block = render_figures(figures, heading="Figures") if figures else ""
    return section + figure_block


def ensure_display_math(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "\\[" in text or "$$" in text:
        return text
    return f"\\[{text}\\]"


def render_formulas(formulas: Iterable[dict]) -> str:
    blocks = []
    for item in formulas or []:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("number") or "Formula"
        text = item.get("text") or item.get("summary") or ""
        latex = item.get("latex") or ""
        parts = [f"<h3>{html_escape(title)}</h3>"]
        if latex:
            parts.append(f"<div class=\"formula-block\">{html_escape(ensure_display_math(latex))}</div>")
        if text:
            parts.append(f"<p>{html_escape(text)}</p>")
        symbols = item.get("symbols") or []
        if isinstance(symbols, list) and symbols:
            rows = []
            for symbol in symbols:
                if isinstance(symbol, dict):
                    rows.append(f"<dt>{html_escape(symbol.get('symbol'))}</dt><dd>{html_escape(symbol.get('text'))}</dd>")
            if rows:
                parts.append(f"<dl class=\"symbol-list\">{''.join(rows)}</dl>")
        blocks.append(f"<section class=\"formula-entry\">{''.join(parts)}</section>")
    return f"<h2>关键公式</h2>{''.join(blocks)}" if blocks else ""


def render_tables(tables: Iterable[dict]) -> str:
    blocks = []
    for item in tables or []:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("number") or "Table"
        text = item.get("text") or item.get("caption") or ""
        summary = item.get("summary") or item.get("conclusion") or ""
        parts = [f"<h3>{html_escape(title)}</h3>"]
        if text:
            parts.append(f"<p>{html_escape(text)}</p>")
        if summary:
            parts.append(f"<p><strong>结论：</strong>{html_escape(summary)}</p>")
        blocks.append(f"<section class=\"table-entry\">{''.join(parts)}</section>")
    return f"<h2>关键表格</h2>{''.join(blocks)}" if blocks else ""


def render_paper_page(paper: dict, all_papers: list[dict], skill_dir: Path, site_title: str = "Conference Papers") -> str:
    note = resolve_internal_links(paper.get("note") or {}, all_papers)
    grouped_figures, unmatched_figures = split_figures_by_section(note.get("figures") or paper.get("figures") or [])
    authors = ", ".join(paper.get("authors", []))
    links = []
    if paper.get("url"):
        links.append(f"<a href=\"{html_escape(paper['url'])}\">Paper</a>")
    if paper.get("pdf_url"):
        links.append(f"<a href=\"{html_escape(paper['pdf_url'])}\">PDF</a>")
    if paper.get("project_url"):
        links.append(f"<a href=\"{html_escape(paper['project_url'])}\">Project</a>")
    note_sections = "\n".join(
        section
        for section in [
            render_note_section("一句话总结", note.get("summary")),
            render_note_section_with_figures("研究背景", note.get("background"), grouped_figures.get("background", [])),
            render_note_section_with_figures("主要贡献", note.get("contributions"), grouped_figures.get("contributions", [])),
            render_note_section_with_figures("研究方法", note.get("method"), grouped_figures.get("method", []), structured=True),
            render_formulas(note.get("formulas") or []),
            render_note_section_with_figures("实验", note.get("experiments"), grouped_figures.get("experiments", []), structured=True),
            render_tables(note.get("tables") or []),
            render_note_section_with_figures("批判性思考", note.get("critical_thinking"), grouped_figures.get("critical_thinking", [])),
            render_note_section_with_figures("相关工作", note.get("related_work"), grouped_figures.get("related_work", [])),
            render_note_section_with_figures("后续工作", note.get("future_work"), grouped_figures.get("future_work", [])),
        ]
        if section
    )
    body = render_template(
        skill_dir,
        "paper-note.html",
        {
            "back_href": "../../index.html",
            "title": html_escape(paper.get("title")),
            "meta": html_escape(f"{paper.get('conference')} {paper.get('year')} · {authors}"),
            "topic_chips": " ".join(f'<span class="chip">{html_escape(t)}</span>' for t in paper.get("topics", [])),
            "links": " · ".join(links),
            "note_sections": note_sections,
            "figures": render_figures(unmatched_figures),
        },
    )
    return page_with_title(paper.get("title", "Paper"), body, prefix="../../", site_title=site_title)


def copy_template_assets(skill_dir: Path, out_dir: Path) -> None:
    assets_src = skill_dir / "assets" / "site-template"
    assets_dst = out_dir / "assets"
    assets_dst.mkdir(parents=True, exist_ok=True)
    for name in ("site.css", "search.js"):
        src = assets_src / name
        if src.exists():
            shutil.copyfile(src, assets_dst / name)


def copy_data_assets(data_dir: Path, out_dir: Path) -> None:
    assets_src = data_dir / "assets"
    if not assets_src.exists():
        return
    assets_dst = out_dir / "assets"
    shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)


def build_static_site(data_dir: Path, out_dir: Path, skill_dir: Path) -> dict:
    config = load_config(skill_dir)
    site_title = str((config.get("site") or {}).get("title") or "Conference Papers")
    papers = load_all_papers(data_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    copy_template_assets(skill_dir, out_dir)
    copy_data_assets(data_dir, out_dir)

    groups: dict[tuple[str, int], list[dict]] = {}
    for paper in papers:
        groups.setdefault((paper.get("conference", "Unknown"), int(paper.get("year", 0))), []).append(paper)

    index_cards = []
    for (conference, year), group in sorted(groups.items(), key=lambda item: (item[0][0].lower(), item[0][1])):
        conf_slug = slugify(conference)
        index_cards.append(
            f"<article class=\"collection-card\"><h2><a href=\"{conf_slug}/index.html\">{html_escape(conference)} {year}</a></h2><p>{len(group)} papers</p></article>"
        )
        conf_dir = out_dir / conf_slug
        conf_dir.mkdir(parents=True, exist_ok=True)
        topic_names = sorted({topic for paper in group for topic in paper.get("topics", [])}, key=str.lower)
        topic_links = " ".join(f"<a class=\"chip\" href=\"{slugify(topic)}/index.html\">{html_escape(topic)}</a>" for topic in topic_names)
        conf_body = render_template(
            skill_dir,
            "collection.html",
            {
                "back_href": "../index.html",
                "page_title": html_escape(f"{conference} {year}"),
                "topic_links": topic_links,
                "paper_list": render_paper_list(group, prefix="../"),
            },
        )
        (conf_dir / "index.html").write_text(page_with_title(f"{conference} {year}", conf_body, prefix="../", site_title=site_title), encoding="utf-8")
        for topic in topic_names:
            topic_dir = conf_dir / slugify(topic)
            topic_dir.mkdir(parents=True, exist_ok=True)
            topic_papers = [paper for paper in group if topic in paper.get("topics", [])]
            topic_body = render_template(
                skill_dir,
                "collection.html",
                {
                    "back_href": "../index.html",
                    "page_title": html_escape(topic),
                    "topic_links": "",
                    "paper_list": render_paper_list(topic_papers, prefix="../../"),
                },
            )
            (topic_dir / "index.html").write_text(page_with_title(f"{conference} {topic}", topic_body, prefix="../../", site_title=site_title), encoding="utf-8")

    paper_root = out_dir / "papers"
    for paper in papers:
        paper_dir = paper_root / paper["id"]
        paper_dir.mkdir(parents=True, exist_ok=True)
        (paper_dir / "index.html").write_text(render_paper_page(paper, papers, skill_dir, site_title=site_title), encoding="utf-8")

    index_body = render_template(
        skill_dir,
        "index.html",
        {
            "page_title": html_escape(site_title),
            "collection_cards": "".join(index_cards) or "<p>No conferences yet.</p>",
            "paper_list": render_paper_list(papers),
        },
    )
    (out_dir / "index.html").write_text(page_with_title(site_title, index_body, site_title=site_title), encoding="utf-8")

    search_index = [
        {
            "id": paper["id"],
            "title": paper.get("title", ""),
            "authors": paper.get("authors", []),
            "conference": paper.get("conference", ""),
            "year": paper.get("year", ""),
            "topics": paper.get("topics", []),
            "abstract": paper.get("abstract", ""),
            "url": f"papers/{paper['id']}/",
        }
        for paper in sorted(papers, key=lambda item: item.get("title", "").lower())
    ]
    write_json(out_dir / "search-index.json", search_index)
    return {"papers": len(papers), "conferences": len(groups), "out": str(out_dir)}
