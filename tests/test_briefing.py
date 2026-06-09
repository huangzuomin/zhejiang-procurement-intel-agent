from procurement_intel.briefing import render_daily_brief
from procurement_intel.classifier import classify_notice
from procurement_intel.models import Notice, OpportunityCard
from procurement_intel.scorer import score_notice


def card(
    title: str,
    content: str,
    *,
    budget: float | None = 200000,
    deadline: str | None = "2026-06-30",
    today: str = "2026-06-08",
) -> OpportunityCard:
    notice = Notice(
        title=title,
        url=f"https://example.test/{title}",
        notice_type="招标公告",
        publish_date=today,
        region="浙江",
        buyer="测试采购人",
        budget=budget,
        deadline=deadline,
        content=content,
    )
    return score_notice(notice, classify_notice(notice), today=today)


def test_renders_mixed_daily_brief_with_focus_sections() -> None:
    cards = [
        card("门户网站建设项目", "门户网站建设、内容管理和运维服务。"),
        card("政务新媒体运营服务", "新媒体运营、账号运营和内容策划。", budget=None),
        card("综合信息化建设项目", "服务器、网络设备和系统集成。"),
        card("办公家具采购项目", "办公桌椅和文件柜。"),
    ]

    message = render_daily_brief("2026-06-08", cards, total_new_notices=10)

    assert "政采情报简报 2026-06-08" in message
    assert "今日新增公告: 10" in message
    assert "值得关注机会: 2" in message
    assert "A 类重点跟进" in message
    assert "B 类值得关注" in message
    assert "门户网站建设项目" in message
    assert "政务新媒体运营服务" in message
    assert "回复项目序号可继续追问" in message


def test_renders_empty_day_brief() -> None:
    message = render_daily_brief("2026-06-08", [], total_new_notices=3)

    assert "今日新增公告: 3" in message
    assert "值得关注机会: 0" in message
    assert "今日暂无 A/B 类重点机会" in message
    assert "监测范围: 浙江政府采购公开公告" in message


def test_long_brief_preserves_a_class_projects_and_summarizes_lower_classes() -> None:
    cards = [
        card("A 类门户网站建设项目", "门户网站建设、内容管理和运维服务。"),
        card("A 类宣传片制作项目", "宣传片、短视频、剪辑和后期制作。"),
        card("B 类 GEO 咨询项目", "GEO、大模型搜索和内容可发现性咨询。"),
        card("C 类信息化项目一", "服务器、网络设备和系统集成。"),
        card("C 类信息化项目二", "服务器、网络设备和系统集成。"),
        card("D 类家具项目", "办公桌椅和文件柜。"),
    ]

    message = render_daily_brief("2026-06-08", cards, total_new_notices=20, max_items_per_class=1)

    assert "A 类门户网站建设项目" in message
    assert "A 类宣传片制作项目" in message
    assert "B 类 GEO 咨询项目" in message
    assert "C/D 类摘要: 3 个低优先级或排除项目" in message
