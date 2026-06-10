#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from procurement_intel.db_briefing import build_brief_from_db


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    brief = build_brief_from_db(
        args.db_path,
        today=args.today,
        mode=args.mode,
        since_brief=args.since_brief,
    )
    paths = {
        "daily_brief": output_dir / "daily_brief.md",
        "summary": output_dir / "summary.json",
    }
    paths["daily_brief"].write_text(brief, encoding="utf-8")
    paths["summary"].write_text(
        json.dumps(
            {
                "today": args.today,
                "mode": args.mode,
                "db_path": args.db_path,
                "outputs": {key: str(path) for key, path in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    payload = {"paths": {key: str(path) for key, path in paths.items()}}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"日报: {paths['daily_brief']}")
        print(f"摘要: {paths['summary']}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate AM/PM procurement briefs from SQLite.")
    parser.add_argument("--mode", choices=["am", "pm"], required=True, help="Brief mode.")
    parser.add_argument("--today", required=True, help="Brief date in YYYY-MM-DD.")
    parser.add_argument("--since-brief", default="am", help="Push-event mode to exclude for PM briefs.")
    parser.add_argument("--db-path", default="data/procurement_intel.db", help="SQLite database path.")
    parser.add_argument("--output-dir", default="reports/latest_daily_pipeline", help="Output directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON output paths.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
