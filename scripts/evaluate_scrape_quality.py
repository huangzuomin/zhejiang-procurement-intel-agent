#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from procurement_intel.scrape_quality import build_cleaned_notices_payload, evaluate_zfcg_scraper_payload


def main() -> int:
    args = parse_args()
    payload = json.loads(Path(args.zfcg_json).read_text(encoding="utf-8"))
    cleaned_notices = build_cleaned_notices_payload(payload)
    report = evaluate_zfcg_scraper_payload(payload, today=args.today)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cleaned_path = output_dir / "cleaned_notices.json"
    report_path = output_dir / "quality_report.json"
    cleaned_path.write_text(json.dumps(cleaned_notices, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"抓取质量等级: {report['quality_grade']}")
    print(f"原始条目: {report['raw_item_count']}")
    print(f"清洗后有效公告: {report['cleaned_notice_count']}")
    print(f"重复条目: {report['duplicate_count']}")
    print(f"噪声条目: {report['noise_count']}")
    print(f"详情链接覆盖: {report['detail_url_count']}/{report['raw_item_count']}")
    print(f"媒体相关: {report['media_relevant_count']}")
    print(f"机会等级分布: {report['opportunity_counts']}")
    print(f"字段缺失: {report['missing_field_counts']}")
    if report["warnings"]:
        print("警告:")
        for warning in report["warnings"]:
            print(f"- {warning}")
    print(f"cleaned_notices: {cleaned_path}")
    print(f"quality_report: {report_path}")

    if args.json:
        print("\nJSON_RESULT_START")
        print(json.dumps({"cleaned_notices_path": str(cleaned_path), "quality_report_path": str(report_path), "quality_report": report}, ensure_ascii=False, indent=2))
        print("JSON_RESULT_END")

    return 0 if report["quality_grade"] != "FAIL" else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate zfcg-scraper JSON data quality.")
    parser.add_argument("zfcg_json", help="Path to zfcg-scraper JSON output.")
    parser.add_argument("--today", default="2026-06-08", help="Date used for scoring.")
    parser.add_argument("--output-dir", default="reports/latest_scrape_quality", help="Directory for cleaned_notices.json and quality_report.json.")
    parser.add_argument("--json", action="store_true", help="Print structured report.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
