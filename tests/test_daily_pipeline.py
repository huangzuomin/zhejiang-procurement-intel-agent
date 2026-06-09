import json

from procurement_intel.daily_pipeline import run_daily_pipeline


def test_daily_pipeline_outputs_column_aware_brief_and_cards(tmp_path) -> None:
    payload = {
        "source": "zfcg_browser_scraper",
        "notices": [
            {
                "title": "门户网站建设与新媒体运营服务公开招标公告",
                "detail_url": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=bid",
                "notice_type": "招标公告",
                "publish_date": "2026-06-09",
                "region": "浙江",
                "category_code": "C16010302行业应用软件开发服务",
                "source_column": "bid",
                "source_column_path": "政府采购公告 > 采购项目公告 > 招标公告",
                "source_category_code": "110-684034",
                "buyer": "浙江某单位",
                "budget": 600000,
                "deadline": "2026-06-30",
                "raw_detail_text": "采购人信息 名称：浙江某单位 预算金额（元）：600000 提交投标文件截止时间：2026年06月30日 采购需求：门户网站建设、内容管理和新媒体运营。",
            },
            {
                "title": "政务新媒体运营服务采购意向",
                "detail_url": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=intention",
                "notice_type": "采购意向公开",
                "publish_date": "2026-06-09",
                "region": "杭州",
                "category_code": "C99000000其他服务",
                "source_column": "intention",
                "source_column_path": "政府采购公告 > 采购意向 > 采购意向公开",
                "source_category_code": "110-600268",
                "buyer": "杭州市某单位",
                "budget": 200000,
                "deadline": None,
                "raw_detail_text": "采购单位 杭州市某单位 预算金额（元）：200000 采购需求概况：政务新媒体运营、账号运营和内容策划。",
            },
        ],
    }
    input_path = tmp_path / "zfcg-two-columns.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = run_daily_pipeline(input_path, output_dir=tmp_path / "out", today="2026-06-09")

    assert result.quality_report["quality_grade"] == "PASS"
    assert result.opportunity_counts["A"] == 1
    assert result.opportunity_counts["B"] == 1
    assert result.paths["cleaned_notices"].exists()
    assert result.paths["opportunity_cards"].exists()
    assert result.paths["daily_brief"].exists()
    assert "招标公告重点机会" in result.daily_brief
    assert "采购意向早期线索" in result.daily_brief
    assert "媒体/数字化相关机会" in result.daily_brief
    assert "门户网站建设与新媒体运营服务公开招标公告" in result.daily_brief
    assert "政务新媒体运营服务采购意向" in result.daily_brief
    assert "立即响应" in result.daily_brief
    assert "提前跟进" in result.daily_brief

    cards = json.loads(result.paths["opportunity_cards"].read_text(encoding="utf-8"))
    assert cards[0]["source_column"] == "bid"
    assert cards[1]["source_column"] == "intention"
