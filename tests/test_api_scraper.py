import importlib.util
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from procurement_intel.hourly_ingestion import ingest_scraper_payload
from procurement_intel.storage import SQLiteStore


spec = importlib.util.spec_from_file_location("zfcg_api_scraper", Path(__file__).resolve().parents[1] / "scripts/zfcg_api_scraper.py")
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)


def test_api_collector_paginates_both_categories_and_fetches_new_details(monkeypatch):
    calls = []

    def fake_fetch(url, *, body=None, **kwargs):
        calls.append((url, body))
        if body:
            page = body["pageNo"]
            code = body["categoryCode"]
            rows = [dict(articleId=f"{code}-{page}-{i}", title=f"采购需求公告 {i}",
                         publishDate=1781053200000, purchaseName="采购单位", budgetPrice="300000") for i in range(15)] if page == 1 else []
            return {"success": True, "result": {"data": {"data": rows}}}
        return {"success": True, "result": {"data": {"content": "<p>采购人：采购单位</p><p>采购需求：网站建设与运营</p>"}}}

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch)
    result = scraper.collect(today="2026-06-10", known_urls=set(), page_limit=3, detail_limit=1, delay_ms=0)
    assert result["collection_status"] == "complete"
    assert [c["pages"] for c in result["columns"]] == [2, 2]
    assert len(result["notices"]) == 30
    assert sum(bool(item["raw_detail_text"]) for item in result["notices"]) == 2
    assert {body["categoryCode"] for _, body in calls if body} == {"110-600268", "110-684034"}


def test_incomplete_collection_fails_without_writing_notices(tmp_path):
    payload = {"source": "zfcg_api_scraper", "collection_status": "partial",
               "columns": [{"key": "intention", "pages": 2}], "notices": [{
                   "title": "网站建设采购", "detail_url": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=abc",
                   "publish_date": "2026-06-10", "buyer": "采购单位", "raw_detail_text": "采购需求：网站建设。"}]}
    db = tmp_path / "db.sqlite"
    result = ingest_scraper_payload(payload, db_path=db, today="2026-06-10")
    store = SQLiteStore(db)
    assert result.quality_grade == "FAIL"
    assert store.get_notice_by_url(payload["notices"][0]["detail_url"]) is None
    with store.connect() as conn:
        assert conn.execute("select status from fetch_runs where run_id = ?", (result.run_id,)).fetchone()[0] == "failed"


def test_delayed_publication_is_included_in_first_seen_day_brief(tmp_path):
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    yesterday = (today - timedelta(days=1)).isoformat()
    payload = {"source": "zfcg_api_scraper", "collection_status": "complete",
               "columns": [{"key": key, "pages": 2, "stop_reason": "older_than_lookback"} for key in ("intention", "bid")],
               "notices": [{"title": "网站建设公开招标", "detail_url": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=late",
                            "notice_type": "招标公告", "publish_date": yesterday, "buyer": "采购单位",
                            "raw_detail_text": "采购人：采购单位。采购需求：网站建设与运营，网站建设与运营。" * 5}]}
    db = tmp_path / "db.sqlite"
    result = ingest_scraper_payload(payload, db_path=db, today=today.isoformat())
    assert result.new_count == 1
    assert [x["title"] for x in SQLiteStore(db).list_cards_for_date(today.isoformat())] == ["网站建设公开招标"]
