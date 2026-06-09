from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .classifier import classify_notice
from .collector import TARGET_MONITOR_URL
from .external_fetcher import zfcg_scraper_payload_to_notices
from .scorer import score_notice


def evaluate_zfcg_scraper_payload(payload: dict[str, Any], *, today: str = "2026-06-08") -> dict[str, Any]:
    raw_items = _raw_items(payload)
    cleaned_notices = zfcg_scraper_payload_to_notices(payload)
    raw_keys = [_item_key(item) for _, item in raw_items]
    raw_titles = [_item_title(item) for _, item in raw_items if _item_title(item)]
    noise_count = sum(1 for _, item in raw_items if _is_noise_item(item))
    duplicate_count = max(0, len(raw_keys) - len(set(raw_keys)))
    title_duplicate_count = max(0, len(raw_titles) - len(set(raw_titles)))
    detail_url_count = sum(1 for _, item in raw_items if _has_detail_url(item))
    detail_url_coverage = _ratio(detail_url_count, len(raw_items))
    missing_link_count = sum(
        1 for _, item in raw_items if not str(item.get("detail_url") or item.get("link") or item.get("url") or "").strip()
    )
    category_counts = Counter(category for category, _ in raw_items)
    repeated_keys = _repeated_categories(raw_items)

    cards = [score_notice(notice, classify_notice(notice), today=today) for notice in cleaned_notices]
    opportunity_counts = Counter(card.opportunity_class for card in cards)
    media_relevant_count = sum(1 for card in cards if card.classification.is_media_relevant)
    media_keyword_hit_count = media_relevant_count
    missing_budget_count = sum(1 for notice in cleaned_notices if notice.budget is None)
    missing_deadline_count = sum(1 for notice in cleaned_notices if not notice.deadline)
    missing_buyer_count = sum(1 for notice in cleaned_notices if not notice.buyer)
    cleaned_payload = build_cleaned_notices_payload(payload)
    raw_detail_text_missing_count = sum(1 for notice in cleaned_payload if notice["raw_detail_text"] is None)

    warnings = _warnings(
        raw_count=len(raw_items),
        cleaned_count=len(cleaned_notices),
        duplicate_count=duplicate_count,
        noise_count=noise_count,
        detail_url_count=detail_url_count,
        missing_budget_count=missing_budget_count,
        missing_deadline_count=missing_deadline_count,
        missing_buyer_count=missing_buyer_count,
        title_duplicate_count=title_duplicate_count,
        raw_detail_text_missing_count=raw_detail_text_missing_count,
    )

    report = {
        "raw_item_count": len(raw_items),
        "cleaned_notice_count": len(cleaned_notices),
        "duplicate_count": duplicate_count,
        "title_duplicate_count": title_duplicate_count,
        "noise_count": noise_count,
        "detail_url_count": detail_url_count,
        "detail_url_coverage": detail_url_coverage,
        "missing_link_count": missing_link_count,
        "category_counts": dict(category_counts),
        "repeated_across_categories_count": len(repeated_keys),
        "media_relevant_count": media_relevant_count,
        "media_keyword_hit_count": media_keyword_hit_count,
        "opportunity_counts": {key: opportunity_counts.get(key, 0) for key in ["A", "B", "C", "D"]},
        "missing_field_counts": {
            "buyer": missing_buyer_count,
            "budget": missing_budget_count,
            "deadline": missing_deadline_count,
        },
        "buyer_missing_count": missing_buyer_count,
        "budget_missing_count": missing_budget_count,
        "deadline_missing_count": missing_deadline_count,
        "raw_detail_text_missing_count": raw_detail_text_missing_count,
        "detail_shell_or_unavailable": bool(cleaned_notices and raw_detail_text_missing_count == len(cleaned_notices)),
        "warnings": warnings,
    }
    report["quality_grade"] = _quality_grade(report)
    return report


def build_cleaned_notices_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    notices = zfcg_scraper_payload_to_notices(payload)
    return [
        {
            "title": notice.title,
            "detail_url": notice.url,
            "notice_type": notice.notice_type,
            "publish_date": notice.publish_date,
            "region": notice.region,
            "category_code": notice.category_code,
            "source_column": notice.source_column,
            "source_column_path": notice.source_column_path,
            "source_category_code": notice.source_category_code,
            "buyer": notice.buyer,
            "budget": notice.budget,
            "deadline": notice.deadline,
            "raw_detail_text": notice.content if _looks_like_real_detail_text(notice.content) else None,
        }
        for notice in notices
    ]


def _raw_items(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    items: list[tuple[str, dict[str, Any]]] = []
    if isinstance(payload.get("notices"), list):
        for item in payload["notices"]:
            category = str(item.get("notice_type") or "公告")
            items.append((category, item))
        return items

    for result in payload.get("results", []):
        category = str(result.get("category") or result.get("type") or "公告")
        for item in result.get("items", []):
            items.append((category, item))
    return items


def _item_key(item: dict[str, Any]) -> str:
    url = str(item.get("detail_url") or item.get("link") or item.get("url") or "").strip()
    if url:
        return url
    return str(item.get("title") or item.get("rawTitle") or "").strip()


def _item_title(item: dict[str, Any]) -> str:
    return str(item.get("title") or item.get("rawTitle") or "").strip()


def _has_detail_url(item: dict[str, Any]) -> bool:
    url = str(item.get("detail_url") or item.get("link") or item.get("url") or "").strip()
    return bool(url and url != TARGET_MONITOR_URL and "/site/detail" in url)


def _is_noise_item(item: dict[str, Any]) -> bool:
    title = str(item.get("title") or item.get("rawTitle") or "").strip()
    url = str(item.get("detail_url") or item.get("link") or item.get("url") or "").strip()
    return title == "网站工作年度报表" or (not url and "报表" in title)


def _repeated_categories(raw_items: list[tuple[str, dict[str, Any]]]) -> dict[str, list[str]]:
    categories_by_key: dict[str, set[str]] = defaultdict(set)
    for category, item in raw_items:
        categories_by_key[_item_key(item)].add(category)
    return {key: sorted(categories) for key, categories in categories_by_key.items() if len(categories) > 1}


def _warnings(
    *,
    raw_count: int,
    cleaned_count: int,
    duplicate_count: int,
    noise_count: int,
    detail_url_count: int,
    missing_budget_count: int,
    missing_deadline_count: int,
    missing_buyer_count: int,
    title_duplicate_count: int,
    raw_detail_text_missing_count: int,
) -> list[str]:
    if raw_count == 0:
        return ["未抓到任何原始条目"]

    warnings = []
    if duplicate_count / raw_count >= 0.25:
        warnings.append("重复率偏高")
    if title_duplicate_count / raw_count >= 0.25:
        warnings.append("同标题重复偏高")
    if noise_count / raw_count >= 0.05:
        warnings.append("导航或页面噪声偏高")
    if detail_url_count / raw_count < 0.8:
        warnings.append("详情链接覆盖不足")
    if cleaned_count == 0:
        warnings.append("清洗后无有效公告")
    if cleaned_count and missing_budget_count == cleaned_count:
        warnings.append("预算字段全部缺失")
    if cleaned_count and missing_deadline_count == cleaned_count:
        warnings.append("截止时间字段全部缺失")
    if cleaned_count and missing_buyer_count == cleaned_count:
        warnings.append("采购人字段全部缺失")
    if cleaned_count and raw_detail_text_missing_count == cleaned_count:
        warnings.append("详情正文未补全或仍为动态页面壳")
    return warnings


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _quality_grade(report: dict[str, Any]) -> str:
    raw_count = report["raw_item_count"]
    cleaned_count = report["cleaned_notice_count"]
    if cleaned_count == 0:
        return "FAIL"
    if raw_count == 0:
        return "FAIL"

    duplicate_rate = report["duplicate_count"] / raw_count
    noise_rate = report["noise_count"] / raw_count
    partial_detail_fields = (
        report["buyer_missing_count"] < cleaned_count
        or report["budget_missing_count"] < cleaned_count
        or report["deadline_missing_count"] < cleaned_count
    )
    if (
        duplicate_rate < 0.10
        and noise_rate < 0.05
        and report["detail_url_coverage"] >= 0.90
        and partial_detail_fields
    ):
        return "PASS"
    if report["detail_url_coverage"] == 0:
        return "FAIL"
    return "WARN"


def _looks_like_real_detail_text(content: str | None) -> bool:
    if not content:
        return False
    shell_markers = ["sourceConfig", "styleValue", "componentTitleColor", "zcy.secondpagesearchlist"]
    if any(marker in content for marker in shell_markers):
        return False
    detail_markers = ["采购人", "采购单位", "预算", "截止时间", "采购需求", "项目基本情况", "联系方式"]
    return len(content.strip()) >= 80 and any(marker in content for marker in detail_markers)
