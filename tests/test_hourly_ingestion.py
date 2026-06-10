from procurement_intel.hourly_ingestion import ingest_scraper_payload
from procurement_intel.storage import SQLiteStore

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hourly_ingestion_is_idempotent(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    payload = {
        "source": "zfcg_browser_scraper",
        "scraped_at": "2026-06-10T09:00:00",
        "notices": [
            {
                "title": "门户网站建设与新媒体运营服务公开招标公告",
                "detail_url": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=bid",
                "notice_type": "招标公告",
                "publish_date": "2026-06-10",
                "region": "浙江",
                "source_column": "bid",
                "buyer": "浙江某单位",
                "budget": 600000,
                "deadline": "2026-06-30",
                "raw_detail_text": "采购需求：门户网站建设、内容管理和新媒体运营。",
            }
        ],
    }

    first = ingest_scraper_payload(payload, db_path=db_path, today="2026-06-10", run_type="hourly")
    second = ingest_scraper_payload(payload, db_path=db_path, today="2026-06-10", run_type="hourly")

    assert first.new_count == 1
    assert second.new_count == 0
    assert SQLiteStore(db_path).count_notices() == 1


def test_run_hourly_ingest_cli_outputs_json_summary(tmp_path):
    input_path = tmp_path / "scrape.json"
    db_path = tmp_path / "procurement_intel.db"
    input_path.write_text(
        json.dumps(
            {
                "source": "zfcg_browser_scraper",
                "notices": [
                    {
                        "title": "政务新媒体运营服务采购意向",
                        "detail_url": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=intention",
                        "notice_type": "采购意向公开",
                        "publish_date": "2026-06-10",
                        "region": "杭州",
                        "source_column": "intention",
                        "buyer": "杭州市某单位",
                        "budget": 200000,
                        "deadline": None,
                        "raw_detail_text": "采购需求概况：政务新媒体运营、账号运营和内容策划。",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "python3",
            "scripts/run_hourly_ingest.py",
            str(input_path),
            "--today",
            "2026-06-10",
            "--db-path",
            str(db_path),
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["new_count"] == 1
    assert payload["quality_grade"] in {"PASS", "WARN"}
    assert payload["opportunity_counts"]["B"] == 1


def test_known_url_detail_skip_preserves_fields_and_score(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    url = "https://zfcg.czt.zj.gov.cn/site/detail?articleId=stable-bid"
    first_payload = {
        "source": "zfcg_browser_scraper",
        "notices": [
            {
                "title": "门户网站建设与新媒体运营服务公开招标公告",
                "detail_url": url,
                "notice_type": "招标公告",
                "publish_date": "2026-06-10",
                "region": "浙江",
                "source_column": "bid",
                "buyer": "浙江某单位",
                "budget": 600000,
                "deadline": "2026-06-30",
                "raw_detail_text": "采购需求：门户网站建设、内容管理和新媒体运营。",
            }
        ],
    }
    second_payload = {
        "source": "zfcg_browser_scraper",
        "notices": [
            {
                "title": "门户网站建设与新媒体运营服务公开招标公告",
                "detail_url": url,
                "notice_type": "招标公告",
                "publish_date": "2026-06-10",
                "region": "浙江",
                "source_column": "bid",
                "buyer": None,
                "budget": None,
                "deadline": None,
                "raw_detail_text": None,
                "known_url": True,
                "detail_skipped_reason": "known_url",
            }
        ],
    }

    ingest_scraper_payload(first_payload, db_path=db_path, today="2026-06-10", run_type="hourly")
    first_card = SQLiteStore(db_path).list_opportunity_cards()[0]
    ingest_scraper_payload(second_payload, db_path=db_path, today="2026-06-10", run_type="hourly")

    store = SQLiteStore(db_path)
    stored = store.get_notice_by_url(url)
    second_card = store.list_opportunity_cards()[0]

    assert stored["buyer"] == "浙江某单位"
    assert stored["budget"] == 600000
    assert stored["deadline"] == "2026-06-30"
    assert first_card["opportunity_class"] == "A"
    assert second_card["opportunity_class"] == "A"


def test_hourly_ingestion_filters_historical_notices_by_default(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    payload = {
        "source": "zfcg_browser_scraper",
        "notices": [
            {
                "title": "历史门户网站建设项目公开招标公告",
                "detail_url": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=old",
                "notice_type": "招标公告",
                "publish_date": "2026-06-01",
                "region": "浙江",
                "source_column": "bid",
                "buyer": "浙江某单位",
                "budget": 600000,
                "deadline": "2026-06-30",
                "raw_detail_text": "采购需求：门户网站建设、内容管理和新媒体运营。",
            },
            {
                "title": "今日门户网站建设项目公开招标公告",
                "detail_url": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=today",
                "notice_type": "招标公告",
                "publish_date": "2026-06-10",
                "region": "浙江",
                "source_column": "bid",
                "buyer": "浙江某单位",
                "budget": 600000,
                "deadline": "2026-06-30",
                "raw_detail_text": "采购需求：门户网站建设、内容管理和新媒体运营。",
            },
        ],
    }

    result = ingest_scraper_payload(payload, db_path=db_path, today="2026-06-10", run_type="hourly")
    cards = SQLiteStore(db_path).list_cards_for_date("2026-06-10")

    assert result.raw_count == 2
    assert result.cleaned_count == 1
    assert result.new_count == 1
    assert [card["title"] for card in cards] == ["今日门户网站建设项目公开招标公告"]
