from __future__ import annotations

from pathlib import Path

from .storage import SQLiteStore


def build_health_report(
    db_path: str | Path,
    *,
    today: str,
    expected_min_raw_count: int = 1,
) -> dict:
    store = SQLiteStore(db_path)
    try:
        hourly_runs = store.list_fetch_runs_for_date(today, run_type="hourly")
        cards = store.list_cards_for_date(today)
    except Exception as error:  # pragma: no cover - defensive runtime guard.
        return {
            "status": "FAIL",
            "today": today,
            "warnings": [f"SQLite 健康检查失败: {error}"],
            "metrics": {},
        }

    successful_runs = [run for run in hourly_runs if run.get("status") == "success"]
    failed_runs = [run for run in hourly_runs if run.get("status") != "success"]
    raw_count = sum(int(run.get("raw_count") or 0) for run in successful_runs)
    new_count = sum(int(run.get("new_count") or 0) for run in successful_runs)
    enriched_count = sum(int(run.get("enriched_count") or 0) for run in successful_runs)
    warnings: list[str] = []

    if not successful_runs:
        warnings.append("当天没有成功的小时采集")
    if successful_runs and raw_count < expected_min_raw_count:
        warnings.append("抓取量低于阈值")
    if failed_runs:
        warnings.append("存在失败的小时采集")

    status = "PASS"
    if not successful_runs:
        status = "FAIL"
    elif warnings:
        status = "WARN"

    return {
        "status": status,
        "today": today,
        "warnings": warnings,
        "metrics": {
            "hourly_run_count": len(hourly_runs),
            "successful_run_count": len(successful_runs),
            "failed_run_count": len(failed_runs),
            "raw_count": raw_count,
            "new_count": new_count,
            "enriched_count": enriched_count,
            "last_successful_run_time": _last_successful_run_time(successful_runs),
            "opportunity_counts": _opportunity_counts(cards),
        },
    }


def _last_successful_run_time(runs: list[dict]) -> str | None:
    values = [run.get("finished_at") or run.get("started_at") for run in runs]
    values = [str(value) for value in values if value]
    return max(values) if values else None


def _opportunity_counts(cards: list[dict]) -> dict[str, int]:
    counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for card in cards:
        opportunity_class = card.get("opportunity_class")
        if opportunity_class in counts:
            counts[str(opportunity_class)] += 1
    return counts
