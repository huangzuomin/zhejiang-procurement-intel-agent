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
