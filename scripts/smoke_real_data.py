#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from procurement_intel.briefing import render_daily_brief
from procurement_intel.classifier import classify_notice
from procurement_intel.collector import DEFAULT_SOURCE_URLS, fetch_public_notice_links, fetch_text
from procurement_intel.external_fetcher import enrich_notice_from_detail_html, load_zfcg_scraper_notices
from procurement_intel.parser import parse_notice_detail
from procurement_intel.scorer import score_notice


def main() -> int:
    args = parse_args()
    cards = []
    errors = []
    detail_urls = args.detail_url[:]

    for zfcg_json in args.zfcg_json:
        try:
            notices = load_zfcg_scraper_notices(zfcg_json)
            if args.enrich_details:
                notices = enrich_notices(notices[: args.limit], timeout=args.detail_timeout, delay=args.detail_delay, errors=errors)
            for notice in notices[: args.limit]:
                classification = classify_notice(notice)
                cards.append(score_notice(notice, classification, today=args.today))
        except Exception as exc:
            errors.append({"zfcg_json": zfcg_json, "error": str(exc)})

    for source_url in args.source_url:
        try:
            links = fetch_public_notice_links(source_url, limit=args.limit, timeout=args.timeout)
        except Exception as exc:
            errors.append({"source_url": source_url, "error": str(exc)})
            continue

        if not links:
            errors.append(
                {
                    "source_url": source_url,
                    "error": "No notice links found in static HTML. The list page may be rendered by JavaScript.",
                }
            )

        for link in links[: args.limit]:
            detail_urls.append(link.url)

    for detail_url in detail_urls[: args.limit]:
        try:
            html = fetch_text(detail_url, timeout=args.timeout)
            notice = parse_notice_detail(
                html,
                url=detail_url,
                notice_type=args.notice_type,
            )
            classification = classify_notice(notice)
            cards.append(score_notice(notice, classification, today=args.today))
        except Exception as exc:
            errors.append({"notice_url": detail_url, "error": str(exc)})

    brief = render_daily_brief(args.today, cards, total_new_notices=len(cards))
    print(brief)

    if args.json:
        payload = {
            "cards": [
                {
                    "title": card.notice.title,
                    "url": card.notice.url,
                    "buyer": card.notice.buyer,
                    "budget": card.notice.budget,
                    "deadline": card.notice.deadline,
                    "category": card.classification.primary_category,
                    "evidence": card.classification.evidence,
                    "opportunity_class": card.opportunity_class,
                    "risks": card.risks,
                    "recommended_action": card.recommended_action,
                }
                for card in cards
            ],
            "errors": errors,
        }
        print("\nJSON_RESULT_START")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("JSON_RESULT_END")

    if errors:
        print(f"\nSmoke completed with {len(errors)} fetch/parse errors.", file=sys.stderr)
    return 0 if cards else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run public real-data smoke test for procurement intelligence.")
    parser.add_argument("--source-url", action="append", default=[], help="Public list page URL. Can be repeated.")
    parser.add_argument("--detail-url", action="append", default=[], help="Public detail page URL. Can be repeated.")
    parser.add_argument("--zfcg-json", action="append", default=[], help="JSON output from OpenClaw zfcg-scraper. Can be repeated.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum notice links per source.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds.")
    parser.add_argument("--detail-timeout", type=int, default=8, help="Detail page timeout seconds for --enrich-details.")
    parser.add_argument("--today", default="2026-06-08", help="Date used for scoring and brief rendering.")
    parser.add_argument("--notice-type", default="公告", help="Notice type label for parsed records.")
    parser.add_argument("--json", action="store_true", help="Print structured cards and errors after the brief.")
    parser.add_argument("--enrich-details", action="store_true", help="Fetch detail pages for --zfcg-json notices before scoring.")
    parser.add_argument("--detail-delay", type=float, default=1.0, help="Seconds to wait between detail page fetches.")
    args = parser.parse_args()
    if not args.source_url and not args.detail_url and not args.zfcg_json:
        args.source_url = DEFAULT_SOURCE_URLS[:1]
    return args


def enrich_notices(notices, *, timeout: int, delay: float, errors: list[dict]):
    enriched = []
    total = len(notices)
    for index, notice in enumerate(notices, start=1):
        try:
            print(f"[detail {index}/{total}] fetching {notice.url}", file=sys.stderr)
            html = fetch_text(notice.url, timeout=timeout)
            enriched.append(enrich_notice_from_detail_html(notice, html))
            print(f"[detail {index}/{total}] ok {notice.title[:60]}", file=sys.stderr)
        except Exception as exc:
            errors.append({"notice_url": notice.url, "title": notice.title, "error": str(exc)})
            enriched.append(notice)
            print(f"[detail {index}/{total}] failed {exc}", file=sys.stderr)
        if delay > 0:
            time.sleep(delay)
    return enriched


if __name__ == "__main__":
    raise SystemExit(main())
