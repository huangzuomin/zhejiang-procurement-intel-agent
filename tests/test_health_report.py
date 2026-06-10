import json
import subprocess
from pathlib import Path

from procurement_intel.classifier import classify_notice
from procurement_intel.health import build_health_report
from procurement_intel.models import Notice
from procurement_intel.scorer import score_notice
from procurement_intel.storage import SQLiteStore


ROOT = Path(__file__).resolve().parents[1]


def test_health_report_flags_low_collection_count(tmp_path):
    store = SQLiteStore(tmp_path / "procurement_intel.db")
    store.initialize()
    store.record_fetch_run(
        run_id="run-low",
        run_type="hourly",
        started_at="2026-06-10T09:00:00",
        finished_at="2026-06-10T09:01:00",
        source="zfcg_browser_scraper",
        raw_count=0,
        new_count=0,
        enriched_count=0,
        status="success",
    )

    report = build_health_report(store.db_path, today="2026-06-10", expected_min_raw_count=10)

    assert report["status"] == "WARN"
    assert "抓取量低于阈值" in report["warnings"]
    assert report["metrics"]["hourly_run_count"] == 1


def test_health_report_fails_when_no_successful_runs(tmp_path):
    store = SQLiteStore(tmp_path / "procurement_intel.db")
    store.initialize()
    store.record_fetch_run(
        run_id="run-failed",
        run_type="hourly",
        started_at="2026-06-10T09:00:00",
        finished_at="2026-06-10T09:01:00",
        source="zfcg_browser_scraper",
        raw_count=0,
        new_count=0,
        enriched_count=0,
        status="failed",
        error="timeout",
    )

    report = build_health_report(store.db_path, today="2026-06-10")

    assert report["status"] == "FAIL"
    assert "当天没有成功的小时采集" in report["warnings"]
    assert report["metrics"]["failed_run_count"] == 1


def test_health_report_counts_opportunity_distribution(tmp_path):
    store = SQLiteStore(tmp_path / "procurement_intel.db")
    store.initialize()
    store.record_fetch_run(
        run_id="run-ok",
        run_type="hourly",
        started_at="2026-06-10T09:00:00",
        finished_at="2026-06-10T09:01:00",
        source="zfcg_browser_scraper",
        raw_count=20,
        new_count=2,
        enriched_count=2,
        status="success",
    )
    _seed_card(store, _notice("门户网站建设公开招标公告", "门户网站建设和运维服务。", "bid"))
    _seed_card(store, _notice("普通办公设备采购公告", "采购办公桌椅。", "bid"))

    report = build_health_report(store.db_path, today="2026-06-10", expected_min_raw_count=10)

    assert report["status"] == "PASS"
    assert report["metrics"]["opportunity_counts"]["A"] == 1
    assert report["metrics"]["opportunity_counts"]["D"] == 1


def test_run_health_report_cli_writes_json(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    output_path = tmp_path / "health_report.json"
    store = SQLiteStore(db_path)
    store.initialize()
    store.record_fetch_run(
        run_id="run-ok",
        run_type="hourly",
        started_at="2026-06-10T09:00:00",
        finished_at="2026-06-10T09:01:00",
        source="zfcg_browser_scraper",
        raw_count=20,
        new_count=2,
        enriched_count=2,
        status="success",
    )

    result = subprocess.run(
        [
            "python3",
            "scripts/run_health_report.py",
            "--today",
            "2026-06-10",
            "--db-path",
            str(db_path),
            "--output",
            str(output_path),
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert output_path.exists()


def _notice(title: str, content: str, source_column: str) -> Notice:
    return Notice(
        title=title,
        url=f"https://zfcg.czt.zj.gov.cn/site/detail?articleId={title}",
        notice_type="招标公告" if source_column == "bid" else "采购意向公开",
        publish_date="2026-06-10",
        region="浙江",
        buyer="浙江某单位",
        budget=600000,
        deadline="2026-06-30" if source_column == "bid" else None,
        content=content,
        source_column=source_column,
    )


def _seed_card(store: SQLiteStore, notice: Notice) -> int:
    notice_id = store.upsert_notice(notice, fetch_run_id="seed", seen_at="2026-06-10T08:00:00")
    card = score_notice(notice, classify_notice(notice), today="2026-06-10")
    store.upsert_opportunity_card(notice_id, card, scored_at="2026-06-10T08:00:00")
    return notice_id
