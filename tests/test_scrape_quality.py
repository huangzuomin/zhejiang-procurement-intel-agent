import json

from procurement_intel.scrape_quality import build_cleaned_notices_payload, evaluate_zfcg_scraper_payload


def test_evaluates_zfcg_scraper_quality_with_duplicates_and_noise() -> None:
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
                    {
                        "title": "办公家具采购项目",
                        "link": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=furniture",
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

    report = evaluate_zfcg_scraper_payload(payload)

    assert report["raw_item_count"] == 4
    assert report["cleaned_notice_count"] == 2
    assert report["duplicate_count"] == 1
    assert report["title_duplicate_count"] == 1
    assert report["noise_count"] == 1
    assert report["detail_url_count"] == 3
    assert report["detail_url_coverage"] == 0.75
    assert report["buyer_missing_count"] == 2
    assert report["budget_missing_count"] == 2
    assert report["deadline_missing_count"] == 2
    assert report["media_keyword_hit_count"] == 1
    assert report["media_relevant_count"] == 1
    assert report["opportunity_counts"]["B"] == 1
    assert report["opportunity_counts"]["D"] == 1
    assert "重复率偏高" in report["warnings"]
    assert "同标题重复偏高" in report["warnings"]
    assert report["quality_grade"] == "WARN"


def test_builds_cleaned_notices_payload_with_required_fields() -> None:
    payload = {
        "results": [
            {
                "category": "公开招标公告",
                "items": [
                    {
                        "title": "[ 杭州市 ·C16080200平台运营服务 ] 政务新媒体运营服务采购项目 2026-06-09",
                        "link": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=media",
                        "date": "",
                        "region": "杭州市 ·C16080200平台运营服务",
                        "category": "C16080200平台运营服务",
                    }
                ],
            }
        ]
    }

    notices = build_cleaned_notices_payload(payload)

    assert notices == [
        {
            "title": "[ 杭州市 ·C16080200平台运营服务 ] 政务新媒体运营服务采购项目 2026-06-09",
            "detail_url": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=media",
            "notice_type": "公开招标公告",
            "publish_date": "2026-06-09",
            "region": "杭州市",
            "category_code": "C16080200平台运营服务",
            "source_column": None,
            "source_column_path": None,
            "source_category_code": None,
            "buyer": None,
            "budget": None,
            "deadline": None,
            "raw_detail_text": None,
        }
    ]


def test_list_text_is_not_treated_as_raw_detail_text() -> None:
    payload = {
        "results": [
            {
                "category": "公开招标公告",
                "items": [
                    {
                        "title": "[ 宁波市 ·A02340800应急救援设备类 ] 宁波市发展和改革委员会本级2026年5月政府采购意向 2026-06-09",
                        "link": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=rescue",
                        "date": "",
                        "category": "A02340800应急救援设备类",
                    }
                ],
            }
        ]
    }

    notices = build_cleaned_notices_payload(payload)

    assert notices[0]["raw_detail_text"] is None


def test_clean_list_payload_still_warns_when_detail_fields_are_missing() -> None:
    payload = {
        "results": [
            {
                "category": "公开招标公告",
                "items": [
                    {
                        "title": "政务新媒体运营服务采购项目",
                        "link": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=media",
                        "date": "2026-06-08",
                    },
                    {
                        "title": "宣传片拍摄制作项目",
                        "link": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=video",
                        "date": "2026-06-08",
                    },
                ],
            }
        ]
    }

    report = evaluate_zfcg_scraper_payload(payload)

    assert report["raw_item_count"] == 2
    assert report["cleaned_notice_count"] == 2
    assert report["duplicate_count"] == 0
    assert report["noise_count"] == 0
    assert report["media_relevant_count"] == 2
    assert "预算字段全部缺失" in report["warnings"]
    assert "截止时间字段全部缺失" in report["warnings"]
    assert report["quality_grade"] == "WARN"


def test_report_flags_missing_real_detail_text() -> None:
    payload = {
        "results": [
            {
                "category": "公开招标公告",
                "items": [
                    {
                        "title": "政务新媒体运营服务采购项目",
                        "link": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=media",
                        "date": "2026-06-09",
                    }
                ],
            }
        ]
    }

    report = evaluate_zfcg_scraper_payload(payload)

    assert report["raw_detail_text_missing_count"] == 1
    assert report["detail_shell_or_unavailable"] is True
    assert "详情正文未补全或仍为动态页面壳" in report["warnings"]


def test_evaluates_browser_scraper_payload_with_detail_text() -> None:
    payload = {
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
                "raw_detail_text": "采购单位 杭州市余杭区中泰幼儿园 采购项目名称 中泰幼儿园大型玩具及户外游戏材料采购 预算金额（元） 700000.00 采购需求概况 标的名称： 中泰幼儿园大型玩具及户外游戏材料采购 需满足的质量、服务、安全、时限等要求： 全新的，符合国家标准的合格产品 联系人 高凯",
            }
        ]
    }

    report = evaluate_zfcg_scraper_payload(payload)
    notices = build_cleaned_notices_payload(payload)

    assert report["raw_item_count"] == 1
    assert report["cleaned_notice_count"] == 1
    assert report["duplicate_count"] == 0
    assert report["noise_count"] == 0
    assert report["detail_url_coverage"] == 1.0
    assert report["missing_link_count"] == 0
    assert report["buyer_missing_count"] == 0
    assert report["budget_missing_count"] == 0
    assert report["raw_detail_text_missing_count"] == 0
    assert report["detail_shell_or_unavailable"] is False
    assert notices[0]["raw_detail_text"] is not None
    assert notices[0]["source_column"] == "intention"
    assert notices[0]["source_column_path"] == "政府采购公告 > 采购意向 > 采购意向公开"
    assert notices[0]["source_category_code"] == "110-600268"
