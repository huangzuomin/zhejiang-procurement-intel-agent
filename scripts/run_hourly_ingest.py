#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from procurement_intel.hourly_ingestion import ingest_scraper_payload


def main() -> int:
    args = parse_args()
    payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    result = ingest_scraper_payload(
        payload,
        db_path=args.db_path,
        today=args.today,
        run_type=args.run_type,
        include_historical=args.include_historical,
    )
    output = {
        "run_id": result.run_id,
        "raw_count": result.raw_count,
        "cleaned_count": result.cleaned_count,
        "new_count": result.new_count,
        "updated_count": result.updated_count,
        "opportunity_counts": result.opportunity_counts,
        "quality_grade": result.quality_grade,
    }
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"run_id: {result.run_id}")
        print(f"raw_count: {result.raw_count}")
        print(f"cleaned_count: {result.cleaned_count}")
        print(f"new_count: {result.new_count}")
        print(f"updated_count: {result.updated_count}")
        print(f"quality_grade: {result.quality_grade}")
        print(f"opportunity_counts: {result.opportunity_counts}")
    return 0 if result.quality_grade != "FAIL" else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest an hourly Zhejiang procurement scraper JSON into SQLite.")
    parser.add_argument("input_json", help="JSON output from the scraper.")
    parser.add_argument("--today", required=True, help="Date used for scoring and quality evaluation.")
    parser.add_argument("--db-path", default="data/procurement_intel.db", help="SQLite database path.")
    parser.add_argument("--run-type", default="hourly", help="Fetch run type label.")
    parser.add_argument(
        "--include-historical",
        action="store_true",
        help="Ingest notices whose publish_date differs from --today. Use only for controlled backfill/bootstrap.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
