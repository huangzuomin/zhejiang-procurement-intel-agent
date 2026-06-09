#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from procurement_intel.daily_pipeline import run_daily_pipeline


def main() -> int:
    args = parse_args()
    result = run_daily_pipeline(args.input_json, output_dir=args.output_dir, today=args.today)

    print(f"日报: {result.paths['daily_brief']}")
    print(f"清洗公告: {result.paths['cleaned_notices']}")
    print(f"机会卡片: {result.paths['opportunity_cards']}")
    print(f"质量报告: {result.paths['quality_report']}")
    print(f"质量等级: {result.quality_report['quality_grade']}")
    print(f"机会分布: {result.opportunity_counts}")
    print(f"媒体/数字化相关: {result.quality_report['media_relevant_count']}")

    if args.json:
        print("\nJSON_RESULT_START")
        print(
            json.dumps(
                {
                    "paths": {key: str(path) for key, path in result.paths.items()},
                    "quality_report": result.quality_report,
                    "opportunity_counts": result.opportunity_counts,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        print("JSON_RESULT_END")
    return 0 if result.quality_report["quality_grade"] != "FAIL" else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the procurement daily intelligence pipeline.")
    parser.add_argument("input_json", help="JSON output from scripts/zfcg_browser_scraper.js.")
    parser.add_argument("--today", default="2026-06-09", help="Date used for scoring and brief rendering.")
    parser.add_argument("--output-dir", default="reports/latest_daily_pipeline", help="Directory for generated artifacts.")
    parser.add_argument("--json", action="store_true", help="Print structured output paths and summary.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
