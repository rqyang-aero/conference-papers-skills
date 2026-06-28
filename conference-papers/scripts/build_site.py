#!/usr/bin/env python3
"""Build the static conference paper reading site."""

from __future__ import annotations

import argparse
from pathlib import Path

from conference_lib import build_static_site, configured_paths, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Render structured paper data to static HTML.")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--config", type=Path, help="Optional config JSON override.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    config = load_config(skill_dir, site_dir=Path.cwd(), config_path=args.config)
    default_data, default_out = configured_paths(config)
    result = build_static_site(args.data or default_data, args.out or default_out, skill_dir)
    print(f"built {result['papers']} papers across {result['conferences']} conferences -> {result['out']}")


if __name__ == "__main__":
    main()
