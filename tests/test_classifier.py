from procurement_intel.classifier import classify_notice
from procurement_intel.models import Notice


def make_notice(title: str, content: str) -> Notice:
    return Notice(
        title=title,
        url="https://example.test/notice/1",
        notice_type="采购意向",
        publish_date="2026-06-08",
        region="浙江",
        buyer="测试采购人",
        budget=120000,
        deadline="2026-06-30",
        content=content,
    )


def test_classifies_website_construction_as_core_opportunity() -> None:
    notice = make_notice(
        "浙江某单位门户网站建设项目",
        "采购内容包括门户网站建设、专题页面设计、内容管理和运维服务。",
    )

    result = classify_notice(notice)

    assert result.primary_category == "网站建设"
    assert result.is_media_relevant is True
    assert result.tier == "core"
    assert "门户网站建设" in result.evidence


def test_classifies_new_media_operation_with_evidence() -> None:
    notice = make_notice(
        "政务新媒体运营服务采购",
        "供应商需负责微信公众号、视频号账号运营、内容策划和数据复盘。",
    )

    result = classify_notice(notice)

    assert result.primary_category == "新媒体运营与运维"
    assert result.is_media_relevant is True
    assert {"新媒体运营", "账号运营"}.issubset(set(result.evidence))


def test_classifies_video_production() -> None:
    notice = make_notice(
        "宣传片拍摄制作项目",
        "服务内容包含宣传片、短视频、摄影摄像、剪辑和后期制作。",
    )

    result = classify_notice(notice)

    assert result.primary_category == "视频拍摄"
    assert result.is_media_relevant is True
    assert "宣传片" in result.evidence


def test_generic_information_project_stays_edge_without_media_subitems() -> None:
    notice = make_notice(
        "综合信息化建设项目",
        "采购内容为服务器、网络设备、机房改造和系统集成服务。",
    )

    result = classify_notice(notice)

    assert result.primary_category == "信息化建设"
    assert result.is_media_relevant is False
    assert result.tier == "edge"
    assert result.confidence == "low"


def test_geo_terms_are_tagged_conservatively() -> None:
    notice = make_notice(
        "AI 搜索优化与内容可发现性服务",
        "围绕大模型搜索、答案引擎优化、GEO 和政务内容可发现性开展咨询。",
    )

    result = classify_notice(notice)

    assert result.primary_category == "GEO / AI 搜索优化 / 内容可发现性"
    assert result.is_media_relevant is True
    assert result.confidence == "medium"
    assert "GEO" in result.evidence


def test_unrelated_procurement_is_excluded() -> None:
    notice = make_notice(
        "办公家具采购项目",
        "采购办公桌椅、文件柜和会议桌等家具。",
    )

    result = classify_notice(notice)

    assert result.primary_category == "无关项目"
    assert result.is_media_relevant is False
    assert result.tier == "excluded"
    assert result.evidence == []
