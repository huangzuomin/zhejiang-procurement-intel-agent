from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .classifier import classify_notice
from .external_fetcher import zfcg_scraper_payload_to_notices
from .scorer import score_notice
from .scrape_quality import evaluate_zfcg_scraper_payload
from .storage import SQLiteStore


@dataclass(frozen=True)
class HourlyIngestResult:
    run_id: str
    raw_count: int
    cleaned_count: int
    new_count: int
    updated_count: int
    opportunity_counts: dict[str, int]
    quality_grade: str


def ingest_scraper_payload(
    payload: dict[str, Any],
    *,
    db_path: str | Path,
    today: str,
    run_type: str = "hourly",
) -> HourlyIngestResult:
    store = SQLiteStore(db_path)
    store.initialize()

    started_at = _now_iso()
    run_id = _run_id(run_type, started_at)
    notices = zfcg_scraper_payload_to_notices(payload)
    raw_count = _raw_count(payload)
    new_count = 0
    opportunity_counts: Counter[str] = Counter()

    for notice in notices:
        was_known = store.get_notice_by_url(notice.url) is not None
        notice_id = store.upsert_notice(notice, fetch_run_id=run_id, seen_at=started_at)
        if not was_known:
            new_count += 1
        card = score_notice(notice, classify_notice(notice), today=today)
        opportunity_counts[card.opportunity_class] += 1
        store.upsert_opportunity_card(notice_id, card, scored_at=started_at)

    quality_report = evaluate_zfcg_scraper_payload(payload, today=today)
    finished_at = _now_iso()
    enriched_count = sum(1 for notice in notices if notice.content and notice.content != notice.title)
    store.record_fetch_run(
        run_id=run_id,
        run_type=run_type,
        started_at=started_at,
        finished_at=finished_at,
        source=str(payload.get("source") or "unknown"),
        raw_count=raw_count,
        new_count=new_count,
        enriched_count=enriched_count,
        status="success",
    )
    store.record_quality_report(
        fetch_run_id=run_id,
        report_json=json.dumps(quality_report, ensure_ascii=False),
        created_at=finished_at,
    )

    return HourlyIngestResult(
        run_id=run_id,
        raw_count=raw_count,
        cleaned_count=len(notices),
        new_count=new_count,
        updated_count=max(0, len(notices) - new_count),
        opportunity_counts={key: opportunity_counts.get(key, 0) for key in ["A", "B", "C", "D"]},
        quality_grade=str(quality_report["quality_grade"]),
    )


def _raw_count(payload: dict[str, Any]) -> int:
    if isinstance(payload.get("notices"), list):
        return len(payload["notices"])
    return sum(len(result.get("items", [])) for result in payload.get("results", []))


def _run_id(run_type: str, timestamp: str) -> str:
    return f"{run_type}-{timestamp.replace(':', '').replace('+', 'Z')}"


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
