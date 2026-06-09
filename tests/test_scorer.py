from procurement_intel.classifier import classify_notice
from procurement_intel.models import Notice
from procurement_intel.scorer import score_notice


def make_notice(
    title: str,
    content: str,
    *,
    budget: float | None = 200000,
    deadline: str | None = "2026-06-30",
    source_column: str | None = None,
) -> Notice:
    return Notice(
        title=title,
        url="https://example.test/notice/2",
        notice_type="招标公告",
        publish_date="2026-06-08",
        region="浙江",
        buyer="测试采购人",
        budget=budget,
        deadline=deadline,
        content=content,
        source_column=source_column,
    )


def test_scores_clear_media_project_as_a_class() -> None:
    notice = make_notice(
        "门户网站建设与新媒体运营服务",
        "包含门户网站建设、微信公众号账号运营、内容策划和一年运维服务。",
    )
    classification = classify_notice(notice)

    card = score_notice(notice, classification, today="2026-06-08")

    assert card.opportunity_class == "A"
    assert "媒体业务匹配明确" in card.reasons
    assert card.risks == []
    assert "重点跟进" in card.recommended_action


def test_scores_geo_project_as_b_when_deliverables_are_early_stage() -> None:
    notice = make_notice(
        "政务内容 GEO 咨询服务",
        "围绕大模型搜索、答案引擎优化和内容可发现性开展咨询。",
        budget=90000,
    )
    classification = classify_notice(notice)

    card = score_notice(notice, classification, today="2026-06-08")

    assert card.opportunity_class == "B"
    assert "GEO 类机会需保守研判" in card.reasons


def test_generic_information_project_scores_as_c() -> None:
    notice = make_notice(
        "综合信息化建设项目",
        "采购内容为服务器、网络设备和系统集成服务。",
    )
    classification = classify_notice(notice)

    card = score_notice(notice, classification, today="2026-06-08")

    assert card.opportunity_class == "C"
    assert "媒体相关证据不足" in card.risks


def test_unrelated_project_scores_as_d() -> None:
    notice = make_notice("办公家具采购项目", "采购办公桌椅和文件柜。")
    classification = classify_notice(notice)

    card = score_notice(notice, classification, today="2026-06-08")

    assert card.opportunity_class == "D"
    assert "无媒体业务匹配证据" in card.risks


def test_low_budget_and_urgent_deadline_add_risks_and_lower_priority() -> None:
    notice = make_notice(
        "宣传片拍摄制作项目",
        "包含宣传片、短视频和后期制作。",
        budget=30000,
        deadline="2026-06-10",
    )
    classification = classify_notice(notice)

    card = score_notice(notice, classification, today="2026-06-08")

    assert card.opportunity_class == "B"
    assert "预算过低" in card.risks
    assert "截止临期" in card.risks


def test_missing_budget_and_deadline_are_reported_without_fabrication() -> None:
    notice = make_notice(
        "政务新媒体运营服务采购意向",
        "负责新媒体运营、内容策划和账号运营。",
        budget=None,
        deadline=None,
    )
    classification = classify_notice(notice)

    card = score_notice(notice, classification, today="2026-06-08")

    assert card.opportunity_class == "B"
    assert card.missing_fields == ["budget", "deadline"]
    assert "信息不足" in card.risks


def test_bid_and_intention_use_different_recommended_actions() -> None:
    content = "包含门户网站建设、内容管理和政务新媒体运营服务。"
    bid_notice = make_notice("门户网站建设招标公告", content, source_column="bid")
    intention_notice = make_notice("门户网站建设采购意向", content, deadline=None, source_column="intention")

    bid_card = score_notice(bid_notice, classify_notice(bid_notice), today="2026-06-08")
    intention_card = score_notice(intention_notice, classify_notice(intention_notice), today="2026-06-08")

    assert "立即响应" in bid_card.recommended_action
    assert "提前跟进" in intention_card.recommended_action
