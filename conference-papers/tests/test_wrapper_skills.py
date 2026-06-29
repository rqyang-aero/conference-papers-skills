from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


EXPECTED = {
    "conference-papers-fetch": {
        "core_delegate": True,
        "terms": ["crawl_conference.py", "add_papers.py", "enrich_arxiv.py"],
    },
    "conference-papers-read": {
        "core_delegate": True,
        "terms": ["generate_note_data.py", "paper-reader", "validate_notes.py"],
    },
    "conference-papers-read2md": {
        "core_delegate": False,
        "terms": [
            "paper_json_context.py",
            "localize_note_images.py",
            "paper-note-template.md",
            "data/_inbox",
            "Obsidian",
            "standalone",
            "online images by default",
            "optional localization",
        ],
    },
    "conference-papers-site": {
        "core_delegate": True,
        "terms": ["build_site.py"],
    },
    "conference-papers-maintain": {
        "core_delegate": True,
        "terms": [
            "add_papers.py",
            "classify_topics.py",
            "enrich_arxiv.py",
            "enrich_fulltext.py",
            "archive_figures.py",
            "validate_notes.py",
            "resolve_links.py",
            "build_site.py",
        ],
    },
}


class WrapperSkillTests(unittest.TestCase):
    def test_wrapper_skills_exist_and_delegate_to_core(self) -> None:
        for name, expectation in EXPECTED.items():
            with self.subTest(name=name):
                skill_dir = ROOT / name
                skill_md = skill_dir / "SKILL.md"
                agent_yaml = skill_dir / "agents" / "openai.yaml"
                self.assertTrue(skill_md.exists(), f"{skill_md} missing")
                self.assertTrue(agent_yaml.exists(), f"{agent_yaml} missing")

                text = skill_md.read_text(encoding="utf-8")
                self.assertIn(f"name: {name}", text)
                self.assertIn("description: Use when", text)
                if expectation["core_delegate"]:
                    self.assertIn("../conference-papers", text)
                for term in expectation["terms"]:
                    self.assertIn(term, text)

                ui = agent_yaml.read_text(encoding="utf-8")
                self.assertIn("default_prompt:", ui)
                self.assertIn(f"${name}", ui)


if __name__ == "__main__":
    unittest.main()
