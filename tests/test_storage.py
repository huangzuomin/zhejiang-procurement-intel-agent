import sqlite3

from procurement_intel.models import Notice
from procurement_intel.classifier import classify_notice
from procurement_intel.scorer import score_notice
from procurement_intel.storage import SQLiteStore


def test_initializes_required_tables(tmp_path):
    db_path = tmp_path / "procurement_intel.db"

    store = SQLiteStore(db_path)
    store.initialize()

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("select name from sqlite_master where type = 'table'")
        }

    assert {
        "fetch_runs",
        "notices",
        "notice_details",
        "opportunity_cards",
        "push_events",
        "quality_reports",
    }.issubset(tables)


def test_upserts_notice_by_detail_url(tmp_path):
    store = SQLiteStore(tmp_path / "procurement_intel.db")
    store.initialize()

    notice = Notice(
        title="政务新媒体运营服务采购意向",
        url="https://zfcg.czt.zj.gov.cn/site/detail?articleId=abc",
        notice_type="采购意向公开",
        publish_date="2026-06-10",
        region="杭州",
        buyer="杭州市某单位",
        budget=200000,
        deadline=None,
        source_column="intention",
    )

    first_id = store.upsert_notice(notice, fetch_run_id="run-1", seen_at="2026-06-10T09:00:00")
    second_id = store.upsert_notice(notice, fetch_run_id="run-2", seen_at="2026-06-10T10:00:00")

    assert first_id == second_id
    assert store.count_notices() == 1
    stored = store.get_notice_by_url(notice.url)
    assert stored is not None
    assert stored["latest_fetch_run_id"] == "run-2"
    assert stored["first_seen_at"] == "2026-06-10T09:00:00"
    assert stored["last_seen_at"] == "2026-06-10T10:00:00"


def test_upserts_opportunity_card_by_notice_id(tmp_path):
    store = SQLiteStore(tmp_path / "procurement_intel.db")
    store.initialize()
    notice = Notice(
        title="门户网站建设与新媒体运营服务公开招标公告",
        url="https://zfcg.czt.zj.gov.cn/site/detail?articleId=bid",
        notice_type="招标公告",
        publish_date="2026-06-10",
        region="浙江",
        buyer="浙江某单位",
        budget=600000,
        deadline="2026-06-30",
        content="采购需求：门户网站建设、内容管理和新媒体运营。",
        source_column="bid",
    )
    notice_id = store.upsert_notice(notice, fetch_run_id="run-1", seen_at="2026-06-10T09:00:00")
    card = score_notice(notice, classify_notice(notice), today="2026-06-10")

    store.upsert_opportunity_card(notice_id, card, scored_at="2026-06-10T09:00:00")
    store.upsert_opportunity_card(notice_id, card, scored_at="2026-06-10T10:00:00")

    cards = store.list_opportunity_cards()
    assert len(cards) == 1
    assert cards[0]["notice_id"] == notice_id
    assert cards[0]["opportunity_class"] == "A"
    assert cards[0]["primary_category"] == card.classification.primary_category
    assert cards[0]["scored_at"] == "2026-06-10T10:00:00"
