#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from procurement_intel.health import build_health_report


def main() -> int:
    args = parse_args()
    report = build_health_report(
        args.db_path,
        today=args.today,
        expected_min_raw_count=args.expected_min_raw_count,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"status: {report['status']}")
        print(f"output: {output}")
    return 0 if report["status"] != "FAIL" else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a SQLite-backed procurement collection health report.")
    parser.add_argument("--today", required=True, help="Report date in YYYY-MM-DD.")
    parser.add_argument("--db-path", default="data/procurement_intel.db", help="SQLite database path.")
    parser.add_argument(
        "--output",
        default="reports/latest_daily_pipeline/health_report.json",
        help="Health report JSON output path.",
    )
    parser.add_argument(
        "--expected-min-raw-count",
        type=int,
        default=1,
        help="Minimum successful hourly raw count before warning.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
