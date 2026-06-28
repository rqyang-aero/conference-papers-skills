#!/usr/bin/env python3
"""Enrich stored papers with arXiv metadata by title matching."""

from __future__ import annotations

import argparse
import copy
import difflib
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

from conference_lib import configured_paths, fetch_text, load_all_papers, load_config, save_paper, strip_tags, unique_ordered


ARXIV_API = "https://export.arxiv.org/api/query"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def direct_children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if local_name(child.tag) == name]


def first_child_text(element: ET.Element, name: str) -> str:
    for child in direct_children(element, name):
        return re.sub(r"\s+", " ", child.text or "").strip()
    return ""


def clean_arxiv_id(value: str) -> str:
    tail = (value or "").strip().rstrip("/").split("/")[-1]
    tail = tail.replace("arXiv:", "")
    return re.sub(r"v\d+$", "", tail)


def arxiv_abs_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""


def arxiv_pdf_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else ""


def parse_arxiv_atom(atom_text: str) -> list[dict]:
    root = ET.fromstring(atom_text)
    entries = [element for element in root.iter() if local_name(element.tag) == "entry"]
    parsed = []
    for entry in entries:
        arxiv_id = clean_arxiv_id(first_child_text(entry, "id"))
        title = first_child_text(entry, "title")
        abstract = strip_tags(first_child_text(entry, "summary"))
        authors = []
        for author in direct_children(entry, "author"):
            name = first_child_text(author, "name")
            if name:
                authors.append(name)
        pdf_url = ""
        for link in direct_children(entry, "link"):
            href = link.attrib.get("href", "")
            marker = " ".join([link.attrib.get("title", ""), link.attrib.get("type", ""), link.attrib.get("rel", "")]).lower()
            if href and ("pdf" in marker or href.lower().endswith(".pdf")):
                pdf_url = href
                break
        parsed.append(
            {
                "title": title,
                "authors": unique_ordered(authors),
                "abstract": abstract,
                "arxiv_id": arxiv_id,
                "arxiv_url": arxiv_abs_url(arxiv_id),
                "pdf_url": arxiv_pdf_url(arxiv_id) or pdf_url.replace("http://", "https://"),
            }
        )
    return [entry for entry in parsed if entry.get("title")]


def normalize_match_text(value: str) -> str:
    value = strip_tags(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def author_key(value: str) -> str:
    parts = re.findall(r"[a-z0-9]+", value.lower())
    return parts[-1] if parts else ""


def title_similarity(left: str, right: str) -> float:
    left_norm = normalize_match_text(left)
    right_norm = normalize_match_text(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    left_tokens = set(left_norm.split())
    right_tokens = set(right_norm.split())
    token_score = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    sequence_score = difflib.SequenceMatcher(None, left_norm, right_norm).ratio()
    return max(token_score, sequence_score)


def author_overlap(left: list[str], right: list[str]) -> float:
    left_keys = {author_key(author) for author in left if author_key(author)}
    right_keys = {author_key(author) for author in right if author_key(author)}
    if not left_keys or not right_keys:
        return 0.0
    return len(left_keys & right_keys) / max(min(len(left_keys), len(right_keys)), 1)


def arxiv_match_score(paper: dict, candidate: dict) -> float:
    title_score = title_similarity(str(paper.get("title") or ""), str(candidate.get("title") or ""))
    author_score = author_overlap(list(paper.get("authors") or []), list(candidate.get("authors") or []))
    return min(1.0, title_score * 0.9 + author_score * 0.1)


def best_arxiv_match(paper: dict, candidates: list[dict], min_score: float = 0.82) -> tuple[dict, float]:
    best: dict = {}
    best_score = 0.0
    for candidate in candidates:
        score = arxiv_match_score(paper, candidate)
        if score > best_score:
            best = candidate
            best_score = score
    return (best, round(best_score, 3)) if best_score >= min_score else ({}, round(best_score, 3))


def merge_arxiv_metadata(paper: dict, arxiv: dict, score: float) -> dict:
    merged = copy.deepcopy(paper)
    if not merged.get("detail_url") and merged.get("url") and "arxiv.org" not in str(merged.get("url")):
        merged["detail_url"] = merged["url"]
    merged["arxiv_id"] = arxiv.get("arxiv_id", "")
    merged["arxiv_url"] = arxiv.get("arxiv_url", "")
    merged["arxiv_match_score"] = round(float(score), 3)
    for field in ("abstract", "pdf_url"):
        if arxiv.get(field) and not merged.get(field):
            merged[field] = arxiv[field]
    if arxiv.get("authors") and not merged.get("authors"):
        merged["authors"] = arxiv["authors"]
    if arxiv.get("arxiv_url") and not merged.get("url"):
        merged["url"] = arxiv["arxiv_url"]
    return merged


def arxiv_query_url(paper: dict, max_results: int = 5) -> str:
    title = str(paper.get("title") or "").replace('"', " ")
    params = {
        "search_query": f'ti:"{title}"',
        "start": "0",
        "max_results": str(max_results),
    }
    return f"{ARXIV_API}?{urllib.parse.urlencode(params)}"


def fetch_arxiv_candidates(paper: dict, max_results: int = 5) -> list[dict]:
    return parse_arxiv_atom(fetch_text(arxiv_query_url(paper, max_results=max_results)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich stored papers with arXiv IDs, abstracts, and PDFs.")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--config", type=Path, help="Optional config JSON override.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=0.82)
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds to wait between arXiv API requests.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    config = load_config(skill_dir, site_dir=Path.cwd(), config_path=args.config)
    default_data, _ = configured_paths(config)
    data_dir = args.data or default_data
    processed = 0
    enriched = 0
    for paper in load_all_papers(data_dir):
        if args.limit and processed >= args.limit:
            break
        if paper.get("arxiv_id"):
            continue
        processed += 1
        try:
            candidates = fetch_arxiv_candidates(paper, max_results=args.max_results)
        except Exception as exc:
            print(f"skip {paper.get('title')}: {exc}")
            continue
        match, score = best_arxiv_match(paper, candidates, min_score=args.min_score)
        if match:
            merged = merge_arxiv_metadata(paper, match, score)
            if not args.dry_run:
                save_paper(data_dir, merged)
            enriched += 1
            print(f"matched {paper.get('title')} -> {match.get('arxiv_id')} ({score:.3f})")
        else:
            print(f"no arXiv match for {paper.get('title')} (best {score:.3f})")
        if args.delay > 0:
            time.sleep(args.delay)
    verb = "would enrich" if args.dry_run else "enriched"
    print(f"{verb} {enriched} of {processed} checked papers")


if __name__ == "__main__":
    main()
