import json

from procurement_intel.briefing import render_daily_brief
from procurement_intel.classifier import classify_notice
from procurement_intel.external_fetcher import (
    enrich_notice_from_detail_html,
    load_zfcg_scraper_notices,
    zfcg_scraper_payload_to_notices,
)
from procurement_intel.models import Notice
from procurement_intel.scorer import score_notice


def test_loads_zfcg_scraper_mvp_json_into_notices(tmp_path) -> None:
    payload = {
        "timestamp": "2026-06-08T08:00:00.000Z",
        "results": [
            {
                "category": "公开招标公告",
                "items": [
                    {
                        "title": "浙江某单位门户网站建设项目公开招标公告",
                        "link": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=abc",
                        "date": "2026-06-08",
                        "region": "杭州",
                        "category": "服务",
                    },
                    {
                        "title": "办公家具采购项目",
                        "link": "",
                        "date": "2026-06-08",
                        "region": "",
                        "category": "货物",
                    },
                ],
            }
        ],
    }
    json_path = tmp_path / "zfcg-mvp.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    notices = load_zfcg_scraper_notices(json_path)

    assert len(notices) == 2
    assert notices[0].title == "浙江某单位门户网站建设项目公开招标公告"
    assert notices[0].url == "https://zfcg.czt.zj.gov.cn/site/detail?articleId=abc"
    assert notices[0].notice_type == "公开招标公告"
    assert notices[0].publish_date == "2026-06-08"
    assert notices[0].region == "杭州"
    assert "门户网站建设" in notices[0].content
    assert notices[1].url == "https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement"


def test_parses_region_and_category_code_from_zfcg_title(tmp_path) -> None:
    payload = {
        "results": [
            {
                "category": "公开招标公告",
                "items": [
                    {
                        "title": "[ 宁波市\n              ·A02340800应急救援设备类  ]   宁波市发展和改革委员会本级2026年5月政府采购意向   2026-06-09",
                        "link": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=abc",
                        "date": "",
                        "region": "宁波市\n              ·A02340800应急救援设备类",
                        "category": "A02340800应急救援设备类",
                    }
                ],
            }
        ],
    }
    json_path = tmp_path / "zfcg.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    notices = load_zfcg_scraper_notices(json_path)

    assert notices[0].region == "宁波市"
    assert notices[0].publish_date == "2026-06-09"


def test_zfcg_scraper_json_runs_through_intelligence_pipeline(tmp_path) -> None:
    payload = {
        "results": [
            {
                "category": "公开招标公告",
                "items": [
                    {
                        "title": "政务新媒体运营服务采购项目",
                        "link": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=media",
                        "date": "2026-06-08",
                    }
                ],
            }
        ]
    }
    json_path = tmp_path / "zfcg.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    notices = load_zfcg_scraper_notices(json_path)
    cards = [score_notice(notice, classify_notice(notice), today="2026-06-08") for notice in notices]
    brief = render_daily_brief("2026-06-08", cards, total_new_notices=len(cards))

    assert cards[0].opportunity_class == "B"
    assert "信息不足" in cards[0].risks
    assert "新媒体运营与运维" in brief
    assert "政务新媒体运营服务采购项目" in brief


def test_filters_navigation_noise_and_deduplicates_by_url(tmp_path) -> None:
    payload = {
        "results": [
            {
                "category": "公开招标公告",
                "items": [
                    {"title": "网站工作年度报表", "link": "", "date": "2026-06-08"},
                    {
                        "title": "浙江某单位门户网站建设项目公开招标公告",
                        "link": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=abc",
                        "date": "2026-06-08",
                    },
                ],
            },
            {
                "category": "采购更正公告",
                "items": [
                    {
                        "title": "浙江某单位门户网站建设项目公开招标公告",
                        "link": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=abc",
                        "date": "2026-06-08",
                    }
                ],
            },
        ]
    }
    json_path = tmp_path / "zfcg.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    notices = load_zfcg_scraper_notices(json_path)

    assert len(notices) == 1
    assert notices[0].title == "浙江某单位门户网站建设项目公开招标公告"


def test_enriches_notice_from_detail_html_without_losing_list_fields() -> None:
    notice = Notice(
        title="浙江某单位门户网站建设项目公开招标公告",
        url="https://zfcg.czt.zj.gov.cn/site/detail?articleId=abc",
        notice_type="公开招标公告",
        publish_date="2026-06-08",
        region="杭州",
        content="浙江某单位门户网站建设项目公开招标公告",
    )
    html = """
    <html>
      <body>
        <h2>浙江某单位门户网站建设项目公开招标公告</h2>
        <div class="vF_detail_content">
          <p>采购人信息 名称：浙江某单位</p>
          <p>预算金额：80万元</p>
          <p>提交投标文件截止时间：2026年06月30日 09:30</p>
          <p>采购需求：门户网站建设、内容管理和新媒体运营。</p>
        </div>
      </body>
    </html>
    """

    enriched = enrich_notice_from_detail_html(notice, html)

    assert enriched.title == notice.title
    assert enriched.url == notice.url
    assert enriched.notice_type == "公开招标公告"
    assert enriched.publish_date == "2026-06-08"
    assert enriched.region == "杭州"
    assert enriched.buyer == "浙江某单位"
    assert enriched.budget == 800000
    assert enriched.deadline == "2026-06-30"
    assert "新媒体运营" in enriched.content


def test_loads_browser_scraper_notices_with_enriched_detail_fields() -> None:
    payload = {
        "source_url": "https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement",
        "scraped_at": "2026-06-09T12:00:00.000Z",
        "notices": [
            {
                "title": "杭州市余杭区中泰幼儿园2026年6月政府采购意向",
                "detail_url": "https://zfcg.czt.zj.gov.cn/site/detail?parentId=600007&articleId=gtFnlHKkBkBaF5grMuQIqg%3D%3D",
                "notice_type": "采购意向公开",
                "publish_date": "2026-06-09",
                "region": "余杭区",
                "category_code": "A05049900其他办公用品",
                "source_column": "intention",
                "source_column_path": "政府采购公告 > 采购意向 > 采购意向公开",
                "source_category_code": "110-600268",
                "buyer": "杭州市余杭区中泰幼儿园",
                "budget": 700000,
                "deadline": None,
                "raw_detail_text": "采购单位 杭州市余杭区中泰幼儿园 采购项目名称 中泰幼儿园大型玩具及户外游戏材料采购 预算金额（元） 700000.00 采购需求概况 标的名称： 中泰幼儿园大型玩具及户外游戏材料采购",
            }
        ],
    }

    notices = zfcg_scraper_payload_to_notices(payload)

    assert len(notices) == 1
    assert notices[0].title == "杭州市余杭区中泰幼儿园2026年6月政府采购意向"
    assert notices[0].url.endswith("articleId=gtFnlHKkBkBaF5grMuQIqg%3D%3D")
    assert notices[0].notice_type == "采购意向公开"
    assert notices[0].publish_date == "2026-06-09"
    assert notices[0].region == "余杭区"
    assert notices[0].category_code == "A05049900其他办公用品"
    assert notices[0].source_column == "intention"
    assert notices[0].source_column_path == "政府采购公告 > 采购意向 > 采购意向公开"
    assert notices[0].source_category_code == "110-600268"
    assert notices[0].buyer == "杭州市余杭区中泰幼儿园"
    assert notices[0].budget == 700000
    assert "采购需求概况" in notices[0].content
