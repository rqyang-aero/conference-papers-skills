from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
READ2MD_SCRIPTS = ROOT / "conference-papers-read2md" / "scripts"
sys.path.insert(0, str(READ2MD_SCRIPTS))

from localize_note_images import process_note  # noqa: E402
from paper_json_context import load_paper_context  # noqa: E402


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


class Read2MdHelperTests(unittest.TestCase):
    def test_paper_json_context_prefers_existing_arxiv_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper_path = root / "data" / "papers" / "method-paper.json"
            paper_path.parent.mkdir(parents=True)
            paper_path.write_text(
                json.dumps(
                    {
                        "id": "method-paper",
                        "title": "MethodPaper: A Strong Robot Learning Method",
                        "conference": "CVPR",
                        "year": 2026,
                        "authors": ["Ada Lovelace", "Alan Turing"],
                        "arxiv_id": "2601.00001",
                        "arxiv_url": "https://arxiv.org/abs/2601.00001",
                        "pdf_url": "",
                        "project_url": "https://example.org/project",
                    }
                ),
                encoding="utf-8",
            )

            context = load_paper_context(paper_path, site_dir=root)

            self.assertEqual(context["id"], "method-paper")
            self.assertEqual(context["title"], "MethodPaper: A Strong Robot Learning Method")
            self.assertEqual(context["venue"], "CVPR")
            self.assertEqual(context["year"], 2026)
            self.assertEqual(context["arxiv_id"], "2601.00001")
            self.assertEqual(context["arxiv_html_url"], "https://arxiv.org/html/2601.00001")
            self.assertEqual(context["primary_source"]["url"], "https://arxiv.org/html/2601.00001")
            self.assertEqual(context["suggested_method_name"], "MethodPaper")
            self.assertEqual(context["output_dir"], "data/_inbox/method-paper")
            self.assertEqual(context["assets_dir"], "data/_inbox/method-paper/assets")

    def test_paper_json_context_supports_title_only_arxiv_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper_path = root / "data" / "papers" / "title-only.json"
            paper_path.parent.mkdir(parents=True)
            paper_path.write_text(
                json.dumps(
                    {
                        "id": "title-only",
                        "title": "Title Only Robot Learning",
                        "authors": ["Grace Hopper"],
                        "conference": "RSS",
                        "year": 2026,
                    }
                ),
                encoding="utf-8",
            )

            context = load_paper_context(paper_path, site_dir=root)

            self.assertEqual(context["primary_source"]["type"], "arxiv_search")
            self.assertIn("Title Only Robot Learning", context["arxiv_search_query"])
            self.assertIn("Grace Hopper", context["arxiv_search_query"])

    def test_paper_json_context_rejects_missing_title_and_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper_path = root / "data" / "papers" / "broken.json"
            paper_path.parent.mkdir(parents=True)
            paper_path.write_text(json.dumps({"id": "broken"}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "title"):
                load_paper_context(paper_path, site_dir=root)

    def test_localize_note_images_stores_assets_and_rewrites_obsidian_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            source.write_bytes(PNG_BYTES)
            note = root / "data" / "_inbox" / "paper-id" / "MethodName.md"
            note.parent.mkdir(parents=True)
            note.write_text(
                f"# MethodName\n\n![Figure 1]({source.as_uri()})\n",
                encoding="utf-8",
            )

            result = process_note(note)

            localized = note.parent / "assets" / "MethodName_fig1.png"
            self.assertEqual(result["total"], 1)
            self.assertEqual(result["localized"], 1)
            self.assertTrue(localized.exists())
            self.assertEqual(localized.read_bytes(), PNG_BYTES)
            self.assertIn("![[assets/MethodName_fig1.png|600]]", note.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
