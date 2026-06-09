from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .briefing import render_column_daily_brief
from .classifier import classify_notice
from .external_fetcher import zfcg_scraper_payload_to_notices
from .models import OpportunityCard
from .scorer import score_notice
from .scrape_quality import build_cleaned_notices_payload, evaluate_zfcg_scraper_payload


@dataclass(frozen=True)
class DailyPipelineResult:
    paths: dict[str, Path]
    daily_brief: str
    quality_report: dict[str, Any]
    opportunity_counts: dict[str, int]


def run_daily_pipeline(input_json: str | Path, *, output_dir: str | Path, today: str) -> DailyPipelineResult:
    input_path = Path(input_json)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    notices = zfcg_scraper_payload_to_notices(payload)
    cards = [score_notice(notice, classify_notice(notice), today=today) for notice in notices]
    quality_report = evaluate_zfcg_scraper_payload(payload, today=today)
    cleaned_notices = build_cleaned_notices_payload(payload)
    card_payload = [_card_to_payload(card) for card in cards]
    opportunity_counts = Counter(card.opportunity_class for card in cards)
    opportunity_counts_payload = {key: opportunity_counts.get(key, 0) for key in ["A", "B", "C", "D"]}
    daily_brief = render_column_daily_brief(today, cards, quality_report=quality_report)

    paths = {
        "cleaned_notices": output_path / "cleaned_notices.json",
        "opportunity_cards": output_path / "opportunity_cards.json",
        "quality_report": output_path / "quality_report.json",
        "daily_brief": output_path / "daily_brief.md",
        "summary": output_path / "summary.json",
    }
    paths["cleaned_notices"].write_text(json.dumps(cleaned_notices, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["opportunity_cards"].write_text(json.dumps(card_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["quality_report"].write_text(json.dumps(quality_report, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["daily_brief"].write_text(daily_brief, encoding="utf-8")
    paths["summary"].write_text(
        json.dumps(
            {
                "input_json": str(input_path),
                "today": today,
                "quality_grade": quality_report["quality_grade"],
                "raw_item_count": quality_report["raw_item_count"],
                "cleaned_notice_count": quality_report["cleaned_notice_count"],
                "category_counts": quality_report["category_counts"],
                "opportunity_counts": opportunity_counts_payload,
                "media_relevant_count": quality_report["media_relevant_count"],
                "warnings": quality_report["warnings"],
                "outputs": {key: str(path) for key, path in paths.items() if key != "summary"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return DailyPipelineResult(
        paths=paths,
        daily_brief=daily_brief,
        quality_report=quality_report,
        opportunity_counts=opportunity_counts_payload,
    )


def _card_to_payload(card: OpportunityCard) -> dict[str, Any]:
    notice = card.notice
    return {
        "title": notice.title,
        "detail_url": notice.url,
        "notice_type": notice.notice_type,
        "source_column": notice.source_column,
        "source_column_path": notice.source_column_path,
        "source_category_code": notice.source_category_code,
        "publish_date": notice.publish_date,
        "region": notice.region,
        "category_code": notice.category_code,
        "buyer": notice.buyer,
        "budget": notice.budget,
        "deadline": notice.deadline,
        "classification": {
            "primary_category": card.classification.primary_category,
            "secondary_categories": card.classification.secondary_categories,
            "evidence": card.classification.evidence,
            "is_media_relevant": card.classification.is_media_relevant,
            "tier": card.classification.tier,
            "confidence": card.classification.confidence,
        },
        "opportunity_class": card.opportunity_class,
        "reasons": card.reasons,
        "risks": card.risks,
        "missing_fields": card.missing_fields,
        "recommended_action": card.recommended_action,
    }
