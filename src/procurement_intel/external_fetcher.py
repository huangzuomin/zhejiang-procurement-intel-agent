from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .collector import TARGET_MONITOR_URL
from .models import Notice
from .parser import parse_notice_detail


def load_zfcg_scraper_notices(json_path: str | Path) -> list[Notice]:
    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
    return zfcg_scraper_payload_to_notices(payload)


def zfcg_scraper_payload_to_notices(payload: dict[str, Any]) -> list[Notice]:
    if isinstance(payload.get("notices"), list):
        return _browser_scraper_payload_to_notices(payload["notices"])

    notices: list[Notice] = []
    seen_keys: set[str] = set()
    for result in payload.get("results", []):
        notice_type = str(result.get("category") or result.get("type") or "公告")
        for item in result.get("items", []):
            notice = _item_to_notice(item, notice_type=notice_type)
            if notice is None:
                continue
            dedupe_key = _dedupe_key(notice)
            if dedupe_key in seen_keys:
                continue
            notices.append(notice)
            seen_keys.add(dedupe_key)
    return notices


def _browser_scraper_payload_to_notices(items: list[dict[str, Any]]) -> list[Notice]:
    notices: list[Notice] = []
    seen_keys: set[str] = set()
    for item in items:
        notice = _browser_item_to_notice(item)
        if notice is None:
            continue
        dedupe_key = _dedupe_key(notice)
        if dedupe_key in seen_keys:
            continue
        notices.append(notice)
        seen_keys.add(dedupe_key)
    return notices


def enrich_notice_from_detail_html(notice: Notice, html: str) -> Notice:
    detail = parse_notice_detail(
        html,
        url=notice.url,
        fallback_title=notice.title,
        notice_type=notice.notice_type,
        region=notice.region,
    )
    return Notice(
        title=notice.title or detail.title,
        url=notice.url,
        notice_type=notice.notice_type,
        publish_date=notice.publish_date or detail.publish_date,
        region=notice.region or detail.region,
        buyer=detail.buyer or notice.buyer,
        budget=detail.budget if detail.budget is not None else notice.budget,
        deadline=detail.deadline or notice.deadline,
        content=detail.content or notice.content,
        category_code=notice.category_code or detail.category_code,
        source_column=notice.source_column,
        source_column_path=notice.source_column_path,
        source_category_code=notice.source_category_code,
    )


def _item_to_notice(item: dict[str, Any], *, notice_type: str) -> Notice | None:
    title = str(item.get("title") or item.get("rawTitle") or "").strip()
    raw_url = str(item.get("link") or item.get("url") or "").strip()
    if not title or _is_navigation_noise(title, raw_url):
        return None

    url = raw_url or TARGET_MONITOR_URL
    title_meta = _parse_title_metadata(title)
    publish_date = _clean_optional(item.get("date") or item.get("publish_date")) or title_meta.get("publish_date")
    region = _normalize_region(_clean_optional(item.get("region"))) or title_meta.get("region") or _infer_region(title)
    category_code = _clean_optional(item.get("category")) or title_meta.get("category_code")
    content_parts = [
        title,
        _clean_optional(item.get("category")),
        _clean_optional(item.get("type")),
        _clean_optional(item.get("rawTitle")),
    ]

    return Notice(
        title=title,
        url=url,
        notice_type=notice_type,
        publish_date=publish_date,
        region=region,
        buyer=None,
        budget=None,
        deadline=None,
        content=" ".join(part for part in content_parts if part),
        category_code=category_code,
    )


def _browser_item_to_notice(item: dict[str, Any]) -> Notice | None:
    title = str(item.get("title") or "").strip()
    raw_url = str(item.get("detail_url") or item.get("link") or item.get("url") or "").strip()
    if not title or _is_navigation_noise(title, raw_url):
        return None

    raw_content = _clean_optional(item.get("raw_detail_text") or item.get("content")) or title
    budget = item.get("budget")
    if isinstance(budget, str):
        budget = _parse_numeric_budget(budget)
    if not isinstance(budget, int | float):
        budget = None

    return Notice(
        title=title,
        url=raw_url or TARGET_MONITOR_URL,
        notice_type=_clean_optional(item.get("notice_type")) or "公告",
        publish_date=_clean_optional(item.get("publish_date")),
        region=_normalize_region(_clean_optional(item.get("region"))),
        buyer=_clean_optional(item.get("buyer")),
        budget=float(budget) if budget is not None else None,
        deadline=_clean_optional(item.get("deadline")),
        content=raw_content,
        category_code=_clean_optional(item.get("category_code")),
        source_column=_clean_optional(item.get("source_column")),
        source_column_path=_clean_optional(item.get("source_column_path")),
        source_category_code=_clean_optional(item.get("source_category_code")),
    )


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_title_metadata(title: str) -> dict[str, str | None]:
    metadata: dict[str, str | None] = {"region": None, "category_code": None, "publish_date": None}
    bracket_match = re.search(r"\[\s*([^\]·]+?)\s*·\s*([^\]]+?)\s*\]", title, re.DOTALL)
    if bracket_match:
        metadata["region"] = _normalize_region(bracket_match.group(1))
        metadata["category_code"] = _clean_whitespace(bracket_match.group(2))
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
    if date_match:
        metadata["publish_date"] = date_match.group(1)
    return metadata


def _normalize_region(value: str | None) -> str | None:
    if not value:
        return None
    clean = _clean_whitespace(value)
    if "·" in clean:
        clean = clean.split("·", 1)[0].strip()
    return clean or None


def _clean_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_numeric_budget(value: str) -> float | None:
    text = value.replace(",", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    amount = float(match.group(1))
    if "万元" in text:
        amount *= 10000
    return amount


def _is_navigation_noise(title: str, url: str) -> bool:
    noise_titles = {"网站工作年度报表"}
    if title.strip() in noise_titles:
        return True
    if not url and "报表" in title:
        return True
    return False


def _dedupe_key(notice: Notice) -> str:
    if notice.url and notice.url != TARGET_MONITOR_URL:
        return notice.url
    return f"{notice.title}|{notice.publish_date or ''}"


def _infer_region(title: str) -> str:
    regions = ["杭州", "宁波", "温州", "绍兴", "湖州", "嘉兴", "金华", "衢州", "舟山", "台州", "丽水"]
    for region in regions:
        if region in title:
            return region
    return "浙江"
