#!/usr/bin/env python3
"""Collect the two public Zhejiang procurement columns via the site's frontend JSON endpoints."""
from __future__ import annotations

import argparse
import html
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BASE = "https://zfcg.czt.zj.gov.cn"
SOURCE_URL = BASE + "/site/category?parentId=600007&childrenCode=ZcyAnnouncement"
SHANGHAI = ZoneInfo("Asia/Shanghai")
TARGETS = {
    "intention": ("110-600268", "采购意向公开", "政府采购公告 > 采购意向 > 采购意向公开"),
    "bid": ("110-684034", "招标公告", "政府采购公告 > 采购项目公告 > 招标公告"),
}


def fetch_json(url: str, *, body: dict | None = None, timeout: float = 30, retries: int = 2) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    headers = {"Accept": "application/json", "Referer": SOURCE_URL, "User-Agent": "Mozilla/5.0 (compatible; procurement-intel/1.0)"}
    if data is not None:
        headers["Content-Type"] = "application/json;charset=UTF-8"
    for attempt in range(retries + 1):
        try:
            with urlopen(Request(url, data=data, headers=headers), timeout=timeout) as response:
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status}: {url}")
                payload = json.load(response)
            if not isinstance(payload, dict) or payload.get("success") is not True:
                raise ValueError(f"Invalid portal response: {url}")
            return payload
        except (HTTPError, URLError, TimeoutError) as exc:
            if isinstance(exc, HTTPError) and exc.code not in (429, 500, 502, 503, 504):
                raise
            if attempt == retries:
                raise
            time.sleep(min(2 ** attempt, 4))
    raise AssertionError("unreachable")


def local_date(milliseconds: int) -> str:
    return datetime.fromtimestamp(milliseconds / 1000, SHANGHAI).date().isoformat()


def clean_html(value: str) -> str:
    value = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", " ", value)
    value = re.sub(r"(?i)<br\s*/?>|</(?:p|div|tr|li|h[1-6])>", "\n", value)
    return re.sub(r"[ \t]+", " ", re.sub(r"(?s)<[^>]+>", " ", html.unescape(value))).strip()


def collect(*, today: str, known_urls: set[str], page_limit: int = 60, detail_limit: int = 900,
            delay_ms: int = 800, timeout: float = 30, lookback_days: int = 2,
            targets: tuple[str, ...] = ("intention", "bid")) -> dict:
    if page_limit < 2 or detail_limit < 0 or lookback_days < 0:
        raise ValueError("page_limit must be >=2, detail_limit and lookback_days must be nonnegative")
    cutoff = (datetime.strptime(today, "%Y-%m-%d").date() - timedelta(days=lookback_days)).isoformat()
    notices: list[dict] = []
    columns: list[dict] = []
    for key in targets:
        code, label, path = TARGETS[key]
        pages = 0
        consecutive_old = 0
        consecutive_known = 0
        reason = "page_limit"
        seen: set[str] = set()
        detail_count = 0
        for page_no in range(1, page_limit + 1):
            response = fetch_json(BASE + "/portal/category", body={"pageNo": page_no, "pageSize": 15, "categoryCode": code}, timeout=timeout)
            page = response.get("result", {}).get("data")
            if not isinstance(page, dict) or not isinstance(page.get("data"), list):
                raise ValueError(f"Unexpected category schema for {key} page {page_no}")
            rows = page["data"]
            pages += 1
            if not rows:
                reason = "empty_page"
                break
            page_dates = []
            page_known = []
            for row in rows:
                if not isinstance(row, dict) or not row.get("articleId") or not row.get("title") or not isinstance(row.get("publishDate"), (int, float)):
                    raise ValueError(f"Unexpected article schema for {key} page {page_no}")
                date = local_date(row["publishDate"])
                page_dates.append(date)
                detail_url = BASE + "/site/detail?" + urlencode({"articleId": row["articleId"]})
                if detail_url in seen:
                    raise ValueError(f"Repeated article in {key}: {detail_url}")
                seen.add(detail_url)
                page_known.append(detail_url in known_urls)
                if date < cutoff:
                    continue
                budget = row.get("budgetPrice")
                try:
                    budget = float(budget) if budget not in (None, "") else None
                except (ValueError, TypeError):
                    budget = None
                notice = {"title": row["title"], "detail_url": detail_url, "notice_type": label,
                          "source_column": key, "source_column_path": path, "source_category_code": code,
                          "publish_date": date, "region": row.get("districtName"),
                          "buyer": row.get("purchaseName"), "budget": budget,
                          "deadline": None, "raw_detail_text": None, "project_name": row.get("projectName")}
                if detail_url in known_urls:
                    notice.update(known_url=True, detail_skipped_reason="known_url")
                elif detail_count < detail_limit:
                    detail_url_api = BASE + "/portal/detail?" + urlencode({"articleId": row["articleId"]})
                    try:
                        detail = fetch_json(detail_url_api, timeout=timeout).get("result", {}).get("data")
                        if not isinstance(detail, dict) or not isinstance(detail.get("content"), str):
                            raise ValueError("Unexpected detail schema")
                        notice["raw_detail_text"] = clean_html(detail["content"]) or None
                        if not notice["raw_detail_text"]:
                            raise ValueError("Empty detail text")
                        notice["portal_detail_url"] = detail_url_api
                    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                        notice["detail_error"] = str(exc)
                    detail_count += 1
                    if delay_ms:
                        time.sleep(delay_ms / 1000)
                else:
                    notice["detail_error"] = "detail_limit_reached"
                notices.append(notice)
            if all(d < cutoff for d in page_dates):
                consecutive_old += 1
                if consecutive_old >= 2:
                    reason = "older_than_lookback"
                    break
            else:
                consecutive_old = 0
            consecutive_known = consecutive_known + 1 if all(page_known) else 0
            if consecutive_known >= 2:
                reason = "already_known"
                break
            if len(rows) < 15:
                reason = "last_page"
                break
            if delay_ms:
                time.sleep(delay_ms / 1000)
        columns.append({"key": key, "category_code": code, "path": path, "pages": pages, "stop_reason": reason})
    return {"source": "zfcg_api_scraper", "source_url": SOURCE_URL,
            "scraped_at": datetime.now(SHANGHAI).isoformat(), "columns": columns,
            "collection_status": "complete" if all(c["stop_reason"] != "page_limit" for c in columns) else "partial",
            "notices": notices}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", required=True)
    parser.add_argument("--known-urls-file", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--page-limit", type=int, default=60)
    parser.add_argument("--detail-limit", type=int, default=900)
    parser.add_argument("--delay-ms", type=int, default=800)
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--lookback-days", type=int, default=2)
    parser.add_argument("--targets", default="intention,bid")
    args = parser.parse_args()
    targets = tuple(args.targets.split(","))
    if not targets or any(target not in TARGETS for target in targets):
        parser.error("--targets must contain intention and/or bid")
    known = set(args.known_urls_file.read_text().splitlines()) if args.known_urls_file and args.known_urls_file.exists() else set()
    payload = collect(today=args.today, known_urls=known, page_limit=args.page_limit,
                      detail_limit=args.detail_limit, delay_ms=args.delay_ms,
                      timeout=args.timeout_ms / 1000, lookback_days=args.lookback_days, targets=targets)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output)
    return 0 if payload["collection_status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
