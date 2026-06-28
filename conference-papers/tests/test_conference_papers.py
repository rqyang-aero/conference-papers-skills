from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from conference_lib import (  # noqa: E402
    build_static_site,
    classify_topics,
    load_config,
    parse_cvf_html,
    parse_rss,
    resolve_internal_links,
)
from archive_figures import archive_paper_figures, resolve_local_path  # noqa: E402
from enrich_arxiv import best_arxiv_match, merge_arxiv_metadata, parse_arxiv_atom  # noqa: E402
from validate_notes import validate_paper_note  # noqa: E402


class ConferencePapersTests(unittest.TestCase):
    def test_cvf_fixture_parses_titles_authors_and_links(self) -> None:
        html = (FIXTURES / "cvf_papers.html").read_text(encoding="utf-8")
        papers = parse_cvf_html(
            html,
            base_url="https://cvpr.thecvf.com/virtual/2026/papers.html",
            conference="CVPR",
            year=2026,
            topics=["VLA", "Humanoid", "locomotion"],
        )

        first = papers[0]
        self.assertEqual(first["title"], "OpenVLA-H: Vision Language Action for Humanoid Locomotion")
        self.assertEqual(first["conference"], "CVPR")
        self.assertEqual(first["year"], 2026)
        self.assertEqual(first["authors"], ["Ada Lovelace", "Alan Turing"])
        self.assertEqual(first["detail_url"], "https://cvpr.thecvf.com/virtual/2026/poster/1001")
        self.assertTrue(first["pdf_url"].endswith("_paper.pdf"))
        self.assertTrue({"VLA", "Humanoid", "locomotion"}.issubset(set(first["topics"])))

    def test_rss_fixture_parses_item_and_preserves_source(self) -> None:
        xml = (FIXTURES / "feed.xml").read_text(encoding="utf-8")
        papers = parse_rss(xml, source_url="https://example.org/feed.xml", conference="RSS", year=2026, topics=["VLA"])

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["title"], "Whole-Body VLA Policies for Humanoid Manipulation")
        self.assertEqual(papers[0]["source"], "rss")
        self.assertEqual(papers[0]["source_url"], "https://example.org/feed.xml")
        self.assertIn("VLA", papers[0]["topics"])

    def test_topic_classification_allows_multiple_topics(self) -> None:
        paper = {
            "title": "OpenVLA-H: Vision Language Action for Humanoid Locomotion",
            "abstract": "A humanoid robot policy for locomotion and loco-manipulation.",
        }

        topics = classify_topics(paper, ["VLA", "Humanoid", "locomotion", "loco-manipulation", "SIGGRAPH"])

        self.assertEqual(topics, ["VLA", "Humanoid", "locomotion", "loco-manipulation"])

    def test_add_papers_merges_duplicate_topics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            manual = FIXTURES / "manual_papers.json"
            cmd = [
                sys.executable,
                str(SCRIPTS / "add_papers.py"),
                "--conference",
                "CVPR",
                "--year",
                "2026",
                "--topic",
                "VLA",
                "--manual",
                str(manual),
                "--data",
                str(data_dir),
                "--draft",
            ]
            subprocess.run(cmd, check=True)
            cmd[cmd.index("VLA")] = "Humanoid"
            subprocess.run(cmd, check=True)

            paper_files = sorted((data_dir / "papers").glob("*.json"))
            self.assertEqual(len(paper_files), 1)
            paper = json.loads(paper_files[0].read_text(encoding="utf-8"))
            self.assertEqual(paper["topics"], ["Humanoid", "VLA"])

    def test_build_site_outputs_core_pages_and_search_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            manual = FIXTURES / "manual_papers.json"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "add_papers.py"),
                    "--conference",
                    "CVPR",
                    "--year",
                    "2026",
                    "--topic",
                    "VLA",
                    "--manual",
                    str(manual),
                    "--data",
                    str(data_dir),
                    "--draft",
                ],
                check=True,
            )
            out_dir = Path(tmp) / "dist"
            subprocess.run([sys.executable, str(SCRIPTS / "build_site.py"), "--data", str(data_dir), "--out", str(out_dir)], check=True)

            self.assertTrue((out_dir / "index.html").exists())
            self.assertTrue((out_dir / "cvpr" / "index.html").exists())
            self.assertTrue((out_dir / "cvpr" / "vla" / "index.html").exists())
            paper_pages = list((out_dir / "papers").glob("*/index.html"))
            self.assertEqual(len(paper_pages), 1)
            search_index = json.loads((out_dir / "search-index.json").read_text(encoding="utf-8"))
            self.assertEqual(search_index[0]["title"], "LocoManip: Loco-Manipulation with Humanoid Robots")
            paper_html = paper_pages[0].read_text(encoding="utf-8")
            index_html = (out_dir / "index.html").read_text(encoding="utf-8")
            topic_html = (out_dir / "cvpr" / "vla" / "index.html").read_text(encoding="utf-8")
            self.assertIn("paper-note-template", paper_html)
            self.assertIn("home-page-template", index_html)
            self.assertIn("collection-page-template", topic_html)

    def test_external_figures_render_inline_by_note_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            paper_dir = data_dir / "papers"
            paper_dir.mkdir(parents=True)
            paper = {
                "id": "sync-paper",
                "title": "SyncPaper: Figure-Text Synchronization",
                "conference": "CVPR",
                "year": 2026,
                "topics": ["VLA"],
                "authors": ["A. Author"],
                "abstract": "A paper for testing figure text synchronization.",
                "url": "https://example.org/sync-paper",
                "pdf_url": "",
                "figures": [],
                "note": {
                    "summary": "One sentence summary.",
                    "background": "Background text.",
                    "contributions": ["Contribution text."],
                    "method": "Method text explains the architecture.",
                    "experiments": "Experiment text explains the results.",
                    "critical_thinking": "Critical text.",
                    "related_work": [],
                    "future_work": [],
                    "figures": [
                        {
                            "number": "Figure 1",
                            "url": "https://example.org/method.png",
                            "caption": "Inline method figure",
                            "section": "method"
                        },
                        {
                            "number": "Figure 2",
                            "url": "https://example.org/experiment.png",
                            "caption": "Inline experiment figure",
                            "section": "experiments"
                        },
                        {
                            "number": "Figure 3",
                            "url": "https://example.org/appendix.png",
                            "caption": "Unclassified appendix figure"
                        }
                    ]
                }
            }
            (paper_dir / "sync-paper.json").write_text(json.dumps(paper), encoding="utf-8")
            out_dir = Path(tmp) / "dist"

            subprocess.run([sys.executable, str(SCRIPTS / "build_site.py"), "--data", str(data_dir), "--out", str(out_dir)], check=True)

            html = (out_dir / "papers" / "sync-paper" / "index.html").read_text(encoding="utf-8")
            method_pos = html.index("研究方法")
            method_fig_pos = html.index("Inline method figure")
            experiment_pos = html.index("实验")
            experiment_fig_pos = html.index("Inline experiment figure")
            critical_pos = html.index("批判性思考")
            appendix_pos = html.index("Unclassified appendix figure")
            self.assertLess(method_pos, method_fig_pos)
            self.assertLess(method_fig_pos, experiment_pos)
            self.assertLess(experiment_pos, experiment_fig_pos)
            self.assertLess(experiment_fig_pos, critical_pos)
            self.assertGreater(appendix_pos, critical_pos)
            self.assertIn('src="https://example.org/method.png"', html)

    def test_template_files_exist_for_page_rendering(self) -> None:
        template_dir = ROOT / "assets" / "site-template"
        expected = {
            "paper-note.html": ["{{title}}", "{{note_sections}}", "{{figures}}"],
            "index.html": ["{{page_title}}", "{{collection_cards}}", "{{paper_list}}"],
            "collection.html": ["{{page_title}}", "{{topic_links}}", "{{paper_list}}"],
        }
        for name, tokens in expected.items():
            with self.subTest(name=name):
                text = (template_dir / name).read_text(encoding="utf-8")
                for token in tokens:
                    self.assertIn(token, text)

    def test_user_config_defaults_and_local_override(self) -> None:
        config_path = ROOT / "config" / "user-config.json"
        self.assertTrue(config_path.exists())
        config = load_config(ROOT)
        self.assertEqual(config["site"]["data_dir"], "data")
        self.assertEqual(config["site"]["output_dir"], "dist")
        self.assertEqual(config["defaults"]["conference"], "CVPR")
        self.assertEqual(config["defaults"]["year"], 2026)
        self.assertIn("VLA", config["defaults"]["topics"])

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "skill"
            config_dir = skill_dir / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "user-config.json").write_text(
                json.dumps({"site": {"data_dir": "data"}, "defaults": {"conference": "CVPR", "year": 2026, "topics": ["VLA"]}}),
                encoding="utf-8",
            )
            (config_dir / "user-config.local.json").write_text(
                json.dumps({"defaults": {"year": 2027, "topics": ["RSS"]}, "site": {"output_dir": "public"}}),
                encoding="utf-8",
            )

            merged = load_config(skill_dir)

        self.assertEqual(merged["site"]["data_dir"], "data")
        self.assertEqual(merged["site"]["output_dir"], "public")
        self.assertEqual(merged["defaults"]["conference"], "CVPR")
        self.assertEqual(merged["defaults"]["year"], 2027)
        self.assertEqual(merged["defaults"]["topics"], ["RSS"])

    def test_cli_uses_config_defaults_for_paths_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manual = FIXTURES / "manual_papers.json"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "add_papers.py"),
                    "--manual",
                    str(manual),
                    "--draft",
                ],
                cwd=tmp_path,
                check=True,
            )
            subprocess.run([sys.executable, str(SCRIPTS / "build_site.py")], cwd=tmp_path, check=True)

            papers = sorted((tmp_path / "data" / "papers").glob("*.json"))
            self.assertEqual(len(papers), 1)
            paper = json.loads(papers[0].read_text(encoding="utf-8"))
            self.assertEqual(paper["conference"], "CVPR")
            self.assertEqual(paper["year"], 2026)
            self.assertIn("Humanoid", paper["topics"])
            self.assertIn("locomotion", paper["topics"])
            self.assertTrue((tmp_path / "dist" / "index.html").exists())
            self.assertTrue((tmp_path / "dist" / "papers" / paper["id"] / "index.html").exists())

    def test_internal_links_resolve_related_and_future_work(self) -> None:
        papers = [
            {"id": "openvla", "title": "OpenVLA: An Open Vision-Language-Action Model"},
            {"id": "locomanip", "title": "LocoManip: Loco-Manipulation with Humanoid Robots"},
        ]
        note = {
            "related_work": [{"title": "OpenVLA", "text": "Builds on OpenVLA."}],
            "future_work": [{"title": "LocoManip", "text": "Could combine with LocoManip."}],
        }

        resolved = resolve_internal_links(note, papers)

        self.assertEqual(resolved["related_work"][0]["paper_id"], "openvla")
        self.assertEqual(resolved["future_work"][0]["paper_id"], "locomanip")

    def test_parse_arxiv_atom_extracts_canonical_metadata(self) -> None:
        atom = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/2601.00001v2</id>
            <title>OpenVLA-H: Vision Language Action for Humanoid Locomotion</title>
            <summary>
              We introduce a vision-language-action policy for humanoid locomotion.
            </summary>
            <author><name>Ada Lovelace</name></author>
            <author><name>Alan Turing</name></author>
            <link href="http://arxiv.org/abs/2601.00001v2" rel="alternate" type="text/html"/>
            <link title="pdf" href="http://arxiv.org/pdf/2601.00001v2" rel="related" type="application/pdf"/>
          </entry>
        </feed>
        """

        entries = parse_arxiv_atom(atom)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["arxiv_id"], "2601.00001")
        self.assertEqual(entries[0]["arxiv_url"], "https://arxiv.org/abs/2601.00001")
        self.assertEqual(entries[0]["pdf_url"], "https://arxiv.org/pdf/2601.00001")
        self.assertEqual(entries[0]["authors"], ["Ada Lovelace", "Alan Turing"])
        self.assertIn("vision-language-action policy", entries[0]["abstract"])

    def test_best_arxiv_match_prefers_title_and_author_overlap(self) -> None:
        paper = {
            "title": "OpenVLA-H: Vision Language Action for Humanoid Locomotion",
            "authors": ["Ada Lovelace", "Alan Turing"],
        }
        candidates = [
            {
                "title": "OpenVLA-H: Vision Language Action for Humanoid Locomotion",
                "authors": ["Ada Lovelace", "Alan Turing"],
                "arxiv_id": "2601.00001",
            },
            {
                "title": "A Survey of Unrelated Rendering Systems",
                "authors": ["Grace Hopper"],
                "arxiv_id": "2601.99999",
            },
        ]

        match, score = best_arxiv_match(paper, candidates, min_score=0.80)

        self.assertEqual(match["arxiv_id"], "2601.00001")
        self.assertGreaterEqual(score, 0.95)

    def test_merge_arxiv_metadata_fills_missing_fields_without_losing_conference_source(self) -> None:
        paper = {
            "id": "openvla-h",
            "title": "OpenVLA-H: Vision Language Action for Humanoid Locomotion",
            "conference": "CVPR",
            "year": 2026,
            "authors": [],
            "abstract": "",
            "url": "https://cvpr.thecvf.com/virtual/2026/poster/1001",
            "detail_url": "https://cvpr.thecvf.com/virtual/2026/poster/1001",
            "pdf_url": "",
            "source": "cvf",
        }
        arxiv = {
            "title": "OpenVLA-H: Vision Language Action for Humanoid Locomotion",
            "authors": ["Ada Lovelace", "Alan Turing"],
            "abstract": "A full arXiv abstract.",
            "arxiv_id": "2601.00001",
            "arxiv_url": "https://arxiv.org/abs/2601.00001",
            "pdf_url": "https://arxiv.org/pdf/2601.00001",
        }

        merged = merge_arxiv_metadata(paper, arxiv, score=0.97)

        self.assertEqual(merged["source"], "cvf")
        self.assertEqual(merged["detail_url"], "https://cvpr.thecvf.com/virtual/2026/poster/1001")
        self.assertEqual(merged["arxiv_id"], "2601.00001")
        self.assertEqual(merged["arxiv_url"], "https://arxiv.org/abs/2601.00001")
        self.assertEqual(merged["pdf_url"], "https://arxiv.org/pdf/2601.00001")
        self.assertEqual(merged["abstract"], "A full arXiv abstract.")
        self.assertEqual(merged["authors"], ["Ada Lovelace", "Alan Turing"])
        self.assertEqual(merged["arxiv_match_score"], 0.97)

    def test_archive_figures_localizes_images_and_build_copies_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            data_dir = tmp_path / "data"
            source = tmp_path / "source.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
            paper = {
                "id": "archive-paper",
                "title": "Archive Paper",
                "conference": "CVPR",
                "year": 2026,
                "topics": ["VLA"],
                "authors": [],
                "abstract": "Archive figure test.",
                "url": "",
                "pdf_url": "",
                "figures": [{"number": "Figure 1", "url": source.as_uri(), "caption": "Overview"}],
                "note": {"summary": "Summary.", "method": "Method.", "figures": []},
            }

            archived = archive_paper_figures(data_dir, paper)
            local_path = archived["figures"][0]["local_path"]
            local_file = resolve_local_path(data_dir, local_path)

            self.assertTrue(local_path.startswith("../../assets/papers/archive-paper/"))
            self.assertTrue(local_file.exists())
            self.assertEqual(local_file.read_bytes(), source.read_bytes())

            paper_dir = data_dir / "papers"
            paper_dir.mkdir(parents=True)
            (paper_dir / "archive-paper.json").write_text(json.dumps(archived), encoding="utf-8")
            out_dir = tmp_path / "dist"
            build_static_site(data_dir, out_dir, ROOT)

            copied = out_dir / "assets" / "papers" / "archive-paper" / local_file.name
            html = (out_dir / "papers" / "archive-paper" / "index.html").read_text(encoding="utf-8")
            self.assertTrue(copied.exists())
            self.assertIn(f'src="{local_path}"', html)

    def test_validate_notes_reports_draft_and_figure_problems(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            paper = {
                "id": "draft-paper",
                "title": "Draft Paper",
                "note": {
                    "mode": "draft",
                    "summary": "Draft summary.",
                    "background": "",
                    "contributions": [],
                    "method": "",
                    "figures": [{"number": "Figure 1", "caption": "Missing source"}],
                    "experiments": "",
                    "critical_thinking": "",
                    "related_work": [],
                    "future_work": [],
                },
            }

            result = validate_paper_note(paper, data_dir=data_dir, check_urls=False)

            self.assertFalse(result["ok"])
            codes = {item["code"] for item in result["findings"]}
            self.assertIn("note_is_draft", codes)
            self.assertIn("missing_required_section", codes)
            self.assertIn("figure_missing_source", codes)

    def test_validate_notes_accepts_final_note_with_local_figure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            fig_path = data_dir / "assets" / "papers" / "final-paper" / "figure-1.png"
            fig_path.parent.mkdir(parents=True)
            fig_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
            paper = {
                "id": "final-paper",
                "title": "Final Paper",
                "note": {
                    "mode": "final",
                    "summary": "Final summary explains the problem, the proposed mechanism, and the evidence from formulas, figures, and tables.",
                    "background": (
                        "Background describes why previous VLA systems struggle with contact-rich manipulation: visual grounding alone "
                        "does not specify force timing, force magnitude, or the transition between free-space motion and contact."
                    ),
                    "contributions": [
                        "Contribution one identifies the physical-control gap in prior VLA policies and introduces explicit force awareness.",
                        "Contribution two connects force prompts, multimodal encoding, and hybrid force-position actions to measurable task success.",
                    ],
                    "method": [
                        {
                            "title": "3.1 Method Overview",
                            "text": (
                                "The method explains how visual tokens, task prompts, force prompts, proprioceptive state, and raw force "
                                "signals are fused before action decoding. It also explains why force information must bypass overly slow "
                                "semantic fusion when contact feedback changes faster than high-level language planning."
                            ),
                        }
                    ],
                    "figures": [
                        {
                            "number": "Figure 1",
                            "local_path": "../../assets/papers/final-paper/figure-1.png",
                            "caption": "Overview.",
                            "section": "method",
                        }
                    ],
                    "formulas": [
                        {
                            "title": "Hybrid action objective",
                            "latex": "J(\\theta)=\\mathbb{E}_{\\tau}[r(\\tau)]",
                            "text": (
                                "The display equation captures the optimized policy objective and is used in the note as mathematical "
                                "evidence instead of being hidden inside a short inline sentence."
                            ),
                        }
                    ],
                    "experiments": [
                        {
                            "title": "Main Results",
                            "text": (
                                "The experiment compares against the primary baselines across multiple contact-rich tasks, reports the "
                                "success-rate gap, and explains which part of the method is supported by the observed improvement."
                            ),
                        }
                    ],
                    "tables": [
                        {
                            "title": "Table 1",
                            "text": "Main result table across contact-rich tasks and baselines.",
                            "summary": "The table supports the claim that force-aware hybrid control improves average success.",
                        }
                    ],
                    "critical_thinking": [
                        {"title": "优点", "text": "The method has clear evidence because figures, formulas, and tables each support a different part of the argument."},
                        {"title": "局限性", "text": "The evaluation scope is limited by hardware assumptions, sensor availability, and the size of the task suite."},
                        {"title": "潜在改进", "text": "Future work can improve robustness by learning force prompts automatically and testing on broader robot embodiments."},
                    ],
                    "related_work": [],
                    "future_work": [],
                    "quality_gate": {
                        "all_figures_verified": True,
                        "all_tables_verified": True,
                        "all_formulas_verified": True,
                    },
                },
            }

            result = validate_paper_note(paper, data_dir=data_dir, check_urls=False)

            self.assertTrue(result["ok"])
            self.assertEqual(result["findings"], [])

    def test_validate_notes_requires_three_critical_thinking_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paper = {
                "id": "critical-paper",
                "title": "Critical Paper",
                "note": {
                    "mode": "final",
                    "summary": "Final summary.",
                    "background": "Background.",
                    "contributions": ["Contribution."],
                    "method": [{"title": "Method", "text": "Method text."}],
                    "figures": [],
                    "experiments": [{"title": "Main Results", "text": "Experiment text."}],
                    "critical_thinking": [
                        {"title": "优点", "text": "Strong empirical evidence."},
                        {"title": "局限性", "text": "Limited domains."},
                    ],
                    "related_work": [],
                    "future_work": [],
                },
            }

            result = validate_paper_note(paper, data_dir=Path(tmp) / "data", check_urls=False)

            self.assertFalse(result["ok"])
            codes = {item["code"] for item in result["findings"]}
            self.assertIn("missing_critical_dimension", codes)

    def test_validate_notes_rejects_string_method_for_final_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paper = {
                "id": "string-method-paper",
                "title": "String Method Paper",
                "note": {
                    "mode": "final",
                    "summary": "Final summary.",
                    "background": "Background.",
                    "contributions": ["Contribution."],
                    "method": "Method as a simple paragraph.",
                    "figures": [],
                    "experiments": [{"title": "Main Results", "text": "Experiment text."}],
                    "critical_thinking": [
                        {"title": "优点", "text": "Strong empirical evidence."},
                        {"title": "局限性", "text": "Limited domains."},
                        {"title": "潜在改进", "text": "Improve robustness."},
                    ],
                    "related_work": [],
                    "future_work": [],
                },
            }

            result = validate_paper_note(paper, data_dir=Path(tmp) / "data", check_urls=False)

            self.assertFalse(result["ok"])
            codes = {item["code"] for item in result["findings"]}
            self.assertIn("invalid_template_section", codes)

    def test_paper_page_includes_mathjax_for_latex_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            paper_dir = data_dir / "papers"
            paper_dir.mkdir(parents=True)
            paper = {
                "id": "formula-paper",
                "title": "Formula Paper",
                "conference": "CVPR",
                "year": 2026,
                "topics": ["VLA"],
                "authors": ["A. Author"],
                "abstract": "A paper with formulas.",
                "url": "https://example.org/formula-paper",
                "note": {
                    "summary": "Formula summary.",
                    "background": "Background.",
                    "contributions": ["Contribution."],
                    "method": [{"title": "3.1 Objective", "text": "Optimize \\[J(\\theta)=\\sum_t r_t\\]."}],
                    "figures": [],
                    "experiments": [{"title": "Main Results", "text": "Experiment text."}],
                    "critical_thinking": [
                        {"title": "优点", "text": "Strong empirical evidence."},
                        {"title": "局限性", "text": "Limited domains."},
                        {"title": "潜在改进", "text": "Improve robustness."},
                    ],
                    "related_work": [],
                    "future_work": [],
                },
            }
            (paper_dir / "formula-paper.json").write_text(json.dumps(paper), encoding="utf-8")
            out_dir = Path(tmp) / "dist"

            build_static_site(data_dir, out_dir, ROOT)

            html = (out_dir / "papers" / "formula-paper" / "index.html").read_text(encoding="utf-8")
            self.assertIn("window.MathJax", html)
            self.assertIn("tex-mml-chtml.js", html)
            self.assertIn("\\[J(\\theta)=\\sum_t r_t\\]", html)

    def test_paper_page_renders_hierarchical_method_and_experiment_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            paper_dir = data_dir / "papers"
            paper_dir.mkdir(parents=True)
            paper = {
                "id": "hierarchy-paper",
                "title": "Hierarchy Paper",
                "conference": "CVPR",
                "year": 2026,
                "topics": ["VLA"],
                "authors": ["A. Author"],
                "abstract": "A paper with nested sections.",
                "url": "https://example.org/hierarchy-paper",
                "note": {
                    "summary": "A deep note summary.",
                    "background": "A detailed background paragraph explaining the task difficulty and prior method gap.",
                    "contributions": ["A contribution grounded in the paper's evidence."],
                    "method": [
                        {
                            "title": "3 ForceVLA2 Framework",
                            "text": "The parent section explains the overall design and why force-aware control is needed.",
                            "subsections": [
                                {
                                    "title": "3.1 Long-Horizon Force Awareness via Prompting",
                                    "text": "This subsection explains stage-level physical prompting and its role in long-horizon task decomposition.",
                                },
                                {
                                    "title": "3.2 Short-Horizon Force-to-Control Loop",
                                    "text": "This subsection explains how raw force bypasses high-level fusion to preserve contact feedback.",
                                },
                            ],
                        }
                    ],
                    "figures": [],
                    "experiments": [
                        {
                            "title": "5 Experiments",
                            "text": "The parent experiment section introduces tasks, baselines, and evaluation protocol.",
                            "subsections": [
                                {
                                    "title": "5.2 Main Experiment Results",
                                    "text": "This subsection interprets the main success-rate table and explains what the gains prove.",
                                }
                            ],
                        }
                    ],
                    "critical_thinking": [
                        {"title": "优点", "text": "The note identifies why the design is compelling."},
                        {"title": "局限性", "text": "The note identifies evaluation and hardware limits."},
                        {"title": "潜在改进", "text": "The note identifies concrete improvements."},
                    ],
                    "related_work": [],
                    "future_work": [],
                },
            }
            (paper_dir / "hierarchy-paper.json").write_text(json.dumps(paper), encoding="utf-8")
            out_dir = Path(tmp) / "dist"

            build_static_site(data_dir, out_dir, ROOT)

            html = (out_dir / "papers" / "hierarchy-paper" / "index.html").read_text(encoding="utf-8")
            parent_pos = html.index("3 ForceVLA2 Framework")
            child_pos = html.index("3.1 Long-Horizon Force Awareness via Prompting")
            experiment_parent_pos = html.index("5 Experiments")
            experiment_child_pos = html.index("5.2 Main Experiment Results")
            self.assertIn('class="note-entry"', html)
            self.assertIn('class="note-subentry"', html)
            self.assertLess(parent_pos, child_pos)
            self.assertLess(experiment_parent_pos, experiment_child_pos)

    def test_paper_page_renders_key_formulas_and_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            paper_dir = data_dir / "papers"
            paper_dir.mkdir(parents=True)
            paper = {
                "id": "evidence-paper",
                "title": "Evidence Paper",
                "conference": "CVPR",
                "year": 2026,
                "topics": ["VLA"],
                "authors": ["A. Author"],
                "abstract": "A paper with formulas and tables.",
                "url": "https://example.org/evidence-paper",
                "note": {
                    "summary": "A formula and table summary.",
                    "background": "Background explains why formula and table evidence matters.",
                    "contributions": ["A contribution supported by equations and experiments."],
                    "method": [{"title": "3.1 Objective", "text": "The method uses a display equation referenced below."}],
                    "figures": [],
                    "formulas": [
                        {
                            "title": "Flow matching action head",
                            "latex": "\\frac{d\\mathbf{a}_t^{(\\tau)}}{d\\tau}=F_\\theta(\\mathbf{a}_t^{(\\tau)},\\mathbf{E}_{MoE},\\tau)",
                            "text": "This equation defines how the action trajectory is integrated from noise to hybrid control.",
                            "symbols": [
                                {"symbol": "\\mathbf{a}_t", "text": "hybrid force-position action"},
                                {"symbol": "\\mathbf{E}_{MoE}", "text": "cross-scale expert representation"},
                            ],
                        }
                    ],
                    "experiments": [{"title": "5.2 Main Results", "text": "The experiment interprets the table below."}],
                    "tables": [
                        {
                            "title": "Table 1",
                            "text": "Success rates across five contact-rich tasks.",
                            "summary": "ForceVLA2 has the best average success rate.",
                        }
                    ],
                    "critical_thinking": [
                        {"title": "优点", "text": "The note ties formulas and tables to the method."},
                        {"title": "局限性", "text": "The note calls out limits in evaluation scope."},
                        {"title": "潜在改进", "text": "The note suggests more robust sensing."},
                    ],
                    "related_work": [],
                    "future_work": [],
                },
            }
            (paper_dir / "evidence-paper.json").write_text(json.dumps(paper), encoding="utf-8")
            out_dir = Path(tmp) / "dist"

            build_static_site(data_dir, out_dir, ROOT)

            html = (out_dir / "papers" / "evidence-paper" / "index.html").read_text(encoding="utf-8")
            self.assertIn("关键公式", html)
            self.assertIn("\\[\\frac{d\\mathbf{a}_t", html)
            self.assertIn("hybrid force-position action", html)
            self.assertIn("关键表格", html)
            self.assertIn("ForceVLA2 has the best average success rate.", html)

    def test_validate_notes_rejects_inline_only_key_formula(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paper = {
                "id": "inline-formula-paper",
                "title": "Inline Formula Paper",
                "note": {
                    "mode": "final",
                    "summary": "Final summary with enough context.",
                    "background": "Background explains the gap in enough detail for a final note.",
                    "contributions": ["Contribution with enough supporting evidence from the paper."],
                    "method": [{"title": "3.1 Objective", "text": "The method explains the objective and cites formula evidence."}],
                    "figures": [{"number": "Figure 1", "url": "https://example.org/fig.png", "caption": "Overview.", "section": "method"}],
                    "formulas": [{"title": "Objective", "text": "The key objective is only inline: \\(J(\\theta)=r\\)."}],
                    "experiments": [{"title": "5.2 Main Results", "text": "Experiments explain metrics, baselines, and conclusions."}],
                    "tables": [{"title": "Table 1", "text": "Main result table with conclusion."}],
                    "critical_thinking": [
                        {"title": "优点", "text": "Strong design with clear evidence from figures and tables."},
                        {"title": "局限性", "text": "Limited benchmark scale and hardware assumptions."},
                        {"title": "潜在改进", "text": "Improve automatic prompt discovery and broader deployment."},
                    ],
                    "related_work": [],
                    "future_work": [],
                    "quality_gate": {
                        "all_figures_verified": True,
                        "all_tables_verified": True,
                        "all_formulas_verified": True,
                    },
                },
            }

            result = validate_paper_note(paper, data_dir=Path(tmp) / "data", check_urls=False)

            self.assertFalse(result["ok"])
            codes = {item["code"] for item in result["findings"]}
            self.assertIn("formula_not_display_math", codes)

    def test_validate_notes_rejects_flattened_section_hierarchy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paper = {
                "id": "flat-section-paper",
                "title": "Flat Section Paper",
                "note": {
                    "mode": "final",
                    "summary": "Final summary with enough context.",
                    "background": "Background explains the gap in enough detail for a final note.",
                    "contributions": ["Contribution with enough supporting evidence from the paper."],
                    "method": [
                        {"title": "3 ForceVLA2 Framework", "text": "Parent method section."},
                        {"title": "3.1 Long-Horizon Force Awareness", "text": "Child method section flattened as a sibling."},
                    ],
                    "figures": [{"number": "Figure 1", "url": "https://example.org/fig.png", "caption": "Overview.", "section": "method"}],
                    "formulas": [{"title": "Objective", "latex": "J(\\theta)=r", "text": "Display formula evidence."}],
                    "experiments": [{"title": "5.2 Main Results", "text": "Experiments explain metrics, baselines, and conclusions."}],
                    "tables": [{"title": "Table 1", "text": "Main result table with conclusion."}],
                    "critical_thinking": [
                        {"title": "优点", "text": "Strong design with clear evidence from figures and tables."},
                        {"title": "局限性", "text": "Limited benchmark scale and hardware assumptions."},
                        {"title": "潜在改进", "text": "Improve automatic prompt discovery and broader deployment."},
                    ],
                    "related_work": [],
                    "future_work": [],
                    "quality_gate": {
                        "all_figures_verified": True,
                        "all_tables_verified": True,
                        "all_formulas_verified": True,
                    },
                },
            }

            result = validate_paper_note(paper, data_dir=Path(tmp) / "data", check_urls=False)

            self.assertFalse(result["ok"])
            codes = {item["code"] for item in result["findings"]}
            self.assertIn("flattened_section_hierarchy", codes)

    def test_validate_notes_rejects_shallow_final_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paper = {
                "id": "shallow-paper",
                "title": "Shallow Paper",
                "note": {
                    "mode": "final",
                    "summary": "Too short.",
                    "background": "Short.",
                    "contributions": ["Brief."],
                    "method": [{"title": "3.1 Method", "text": "Brief."}],
                    "figures": [{"number": "Figure 1", "url": "https://example.org/fig.png", "caption": "Overview.", "section": "method"}],
                    "formulas": [{"title": "Objective", "latex": "J(\\theta)=r", "text": "Brief."}],
                    "experiments": [{"title": "5.2 Results", "text": "Brief."}],
                    "tables": [{"title": "Table 1", "text": "Brief."}],
                    "critical_thinking": [
                        {"title": "优点", "text": "Brief."},
                        {"title": "局限性", "text": "Brief."},
                        {"title": "潜在改进", "text": "Brief."},
                    ],
                    "related_work": [],
                    "future_work": [],
                    "quality_gate": {
                        "all_figures_verified": True,
                        "all_tables_verified": True,
                        "all_formulas_verified": True,
                    },
                },
            }

            result = validate_paper_note(paper, data_dir=Path(tmp) / "data", check_urls=False)

            self.assertFalse(result["ok"])
            codes = {item["code"] for item in result["findings"]}
            self.assertIn("insufficient_note_depth", codes)

if __name__ == "__main__":
    unittest.main()
