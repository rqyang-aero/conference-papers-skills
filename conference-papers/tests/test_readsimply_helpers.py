from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
READSIMPLY_SKILL = ROOT / "conference-papers-readsimply"
READSIMPLY_TEMPLATE = READSIMPLY_SKILL / "assets" / "paper-note-template.md"
READSIMPLY_SKILL_MD = READSIMPLY_SKILL / "SKILL.md"
READSIMPLY_SCRIPTS = READSIMPLY_SKILL / "scripts"
for module_name in ("arxiv_html_metadata", "batch_paper_json_context", "paper_json_context"):
    sys.modules.pop(module_name, None)
sys.path.insert(0, str(READSIMPLY_SCRIPTS))

from arxiv_html_metadata import parse_arxiv_html_metadata  # noqa: E402
from batch_paper_json_context import load_batch_contexts  # noqa: E402
from paper_json_context import load_paper_context  # noqa: E402


def write_paper(path: Path, **overrides: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, object] = {
        "id": path.stem,
        "title": f"{path.stem.title()}: A Robot Paper",
        "authors": ["Ada Lovelace", "Alan Turing"],
        "conference": "RSS",
        "year": 2026,
        "topics": ["VLA"],
        "abstract": "This paper introduces a fast robot learning method.",
        "arxiv_id": "2601.00001",
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")


class ReadSimplyHelperTests(unittest.TestCase):
    def test_template_only_contains_metadata_and_one_sentence_summary(self) -> None:
        text = READSIMPLY_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("# {Title}", text)
        self.assertIn("## 元信息", text)
        self.assertIn("## 一句话总结", text)
        self.assertIn("| 作者 | {Authors} |", text)
        self.assertIn("| 会议 | {Venue} {Year} |", text)
        self.assertIn("| 类别 | {topics} |", text)
        self.assertNotIn("## 核心贡献", text)
        self.assertNotIn("## 问题背景", text)
        self.assertNotIn("## 方法详解", text)
        self.assertNotIn("## 关键图表", text)
        self.assertNotIn("## 实验", text)
        self.assertNotIn("## 批判性思考", text)
        self.assertNotIn("## 速查卡片", text)

    def test_skill_is_abstract_only_and_forbids_full_paper_reading(self) -> None:
        text = READSIMPLY_SKILL_MD.read_text(encoding="utf-8")

        self.assertIn("abstract only", text)
        self.assertIn("只阅读 abstract", text)
        self.assertIn("Read arXiv HTML abstract metadata", text)
        self.assertIn("只读取 arXiv HTML 的摘要和元信息", text)
        self.assertIn("Do not read arXiv HTML body after the abstract", text)
        self.assertIn("Do not download or parse PDFs", text)
        self.assertIn("Do not create `assets/`", text)

    def test_arxiv_html_metadata_parser_extracts_only_abstract_block(self) -> None:
        html = """
        <html>
          <body>
            <h1 class="ltx_title ltx_title_document">Title: SpatialVLA: Exploring Spatial Representations</h1>
            <div class="ltx_authors">
              <span class="ltx_personname">
                Ada Lovelace<sup>1</sup>, Alan Turing<sup>2</sup>
                <br class="ltx_break"/>
                <sup>1</sup>Analytical Engine Lab,
                <sup>2</sup>Computing University
              </span>
              <span class="ltx_author_notes">Corresponding author: ada@example.com</span>
            </div>
            <div class="ltx_dates">Submitted on 1 Jan 2026</div>
            <section class="ltx_abstract">
              <h6 class="ltx_title ltx_title_abstract">Abstract</h6>
              <p>We study spatial representations for visual-language-action models.</p>
            </section>
            <section class="ltx_section">
              <h2>Introduction</h2>
              <p>This method detail must not be captured.</p>
            </section>
          </body>
        </html>
        """

        metadata = parse_arxiv_html_metadata(html, url="https://arxiv.org/html/2601.00001")

        self.assertEqual(metadata["title"], "SpatialVLA: Exploring Spatial Representations")
        self.assertEqual(metadata["authors"], ["Ada Lovelace", "Alan Turing"])
        self.assertEqual(metadata["date"], "Submitted on 1 Jan 2026")
        self.assertEqual(
            metadata["abstract"],
            "We study spatial representations for visual-language-action models.",
        )
        self.assertNotIn("Introduction", metadata["abstract"])
        self.assertNotIn("method detail", metadata["abstract"])

    def test_paper_json_context_uses_simple_note_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "data" / "papers" / "fast-paper.json"
            write_paper(paper, title="FAST: Efficient Action Tokenization")

            context = load_paper_context(paper, site_dir=root)

            self.assertEqual(context["id"], "fast-paper")
            self.assertEqual(context["suggested_method_name"], "FAST")
            self.assertEqual(context["output_dir"], "data/_inbox/fast-paper")
            self.assertEqual(context["simple_note_path"], "data/_inbox/fast-paper/FAST-simple.md")
            self.assertEqual(context["primary_source"]["type"], "arxiv_html_abstract")
            self.assertEqual(context["primary_source"]["url"], "https://arxiv.org/html/2601.00001")
            self.assertNotIn("assets_dir", context)

    def test_batch_contexts_support_paths_globs_directories_and_deduplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            papers = root / "data" / "papers"
            write_paper(papers / "alpha.json", id="shared", title="ALPHA: First")
            write_paper(papers / "beta.json", id="beta", title="BETA: Second")
            write_paper(papers / "duplicate.json", id="shared", title="ALPHA Duplicate: First")

            result = load_batch_contexts(
                [
                    papers / "alpha.json",
                    str(papers / "*.json"),
                    papers,
                ],
                site_dir=root,
            )

            self.assertEqual(result["failed"], 0)
            self.assertEqual([item["id"] for item in result["items"]], ["shared", "beta"])
            self.assertEqual(result["count"], 2)

    def test_batch_contexts_record_bad_json_without_blocking_good_papers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            papers = root / "data" / "papers"
            write_paper(papers / "good.json", id="good", title="GOOD: Works")
            bad = papers / "bad.json"
            bad.parent.mkdir(parents=True, exist_ok=True)
            bad.write_text("{broken", encoding="utf-8")

            result = load_batch_contexts([papers], site_dir=root)

            self.assertEqual([item["id"] for item in result["items"]], ["good"])
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["failed"], 1)
            self.assertIn("bad.json", result["failures"][0]["reference"])


if __name__ == "__main__":
    unittest.main()
