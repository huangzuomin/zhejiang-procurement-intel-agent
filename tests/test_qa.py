from procurement_intel.classifier import classify_notice
from procurement_intel.models import Notice, OpportunityCard
import json

from procurement_intel.qa import answer_question, answer_question_from_cards_file, load_opportunity_cards
from procurement_intel.scorer import score_notice


def card(title: str, content: str) -> OpportunityCard:
    notice = Notice(
        title=title,
        url=f"https://example.test/{title}",
        notice_type="招标公告",
        publish_date="2026-06-08",
        region="浙江",
        buyer="测试采购人",
        budget=180000,
        deadline="2026-06-30",
        content=content,
    )
    return score_notice(notice, classify_notice(notice), today="2026-06-08")


def card_payload(
    title: str,
    *,
    source_column: str,
    notice_type: str,
    buyer: str,
    opportunity_class: str,
    recommended_action: str,
) -> dict:
    return {
        "title": title,
        "detail_url": f"https://example.test/{title}",
        "notice_type": notice_type,
        "source_column": source_column,
        "source_column_path": "政府采购公告 > 采购项目公告 > 招标公告" if source_column == "bid" else "政府采购公告 > 采购意向 > 采购意向公开",
        "source_category_code": "110-684034" if source_column == "bid" else "110-600268",
        "publish_date": "2026-06-09",
        "region": "浙江",
        "category_code": "C99000000其他服务",
        "buyer": buyer,
        "budget": 600000,
        "deadline": "2026-06-30" if source_column == "bid" else None,
        "classification": {
            "primary_category": "新媒体运营与运维",
            "secondary_categories": [],
            "evidence": ["新媒体运营"],
            "is_media_relevant": True,
            "tier": "core",
            "confidence": "high",
        },
        "opportunity_class": opportunity_class,
        "reasons": ["媒体业务匹配明确"],
        "risks": [] if source_column == "bid" else ["信息不足"],
        "missing_fields": [] if source_column == "bid" else ["deadline"],
        "recommended_action": recommended_action,
    }


def test_answers_exact_project_reference_from_existing_card() -> None:
    cards = [
        card("门户网站建设项目", "门户网站建设、内容管理和运维服务。"),
        card("宣传片拍摄制作项目", "宣传片、短视频和后期制作。"),
    ]

    answer = answer_question("门户网站建设项目适合我们跟进吗？", cards)

    assert "结论: A" in answer
    assert "门户网站建设项目" in answer
    assert "证据:" in answer
    assert "建议:" in answer
    assert "https://example.test/门户网站建设项目" in answer


def test_asks_for_clarification_when_fuzzy_reference_matches_multiple_cards() -> None:
    cards = [
        card("门户网站建设项目", "门户网站建设、内容管理和运维服务。"),
        card("专题网站建设项目", "网站建设、专题页面和内容管理。"),
    ]

    answer = answer_question("网站建设这个项目风险是什么？", cards)

    assert "找到多个可能项目" in answer
    assert "门户网站建设项目" in answer
    assert "专题网站建设项目" in answer


def test_refuses_out_of_scope_bid_execution_request() -> None:
    cards = [card("门户网站建设项目", "门户网站建设、内容管理和运维服务。")]

    answer = answer_question("帮我报名并提交这个项目的投标文件", cards)

    assert "不能代办报名、提交投标文件或执行投标流程" in answer
    assert "可以帮你做情报研判" in answer


def test_reports_unknown_project_without_fabricating() -> None:
    cards = [card("门户网站建设项目", "门户网站建设、内容管理和运维服务。")]

    answer = answer_question("家具采购项目值得看吗？", cards)

    assert "没有在已采集机会卡中定位到该项目" in answer
    assert "不会补编未采集事实" in answer


def test_loads_latest_opportunity_cards_json_and_answers_focus_questions(tmp_path) -> None:
    cards_path = tmp_path / "opportunity_cards.json"
    cards_path.write_text(
        json.dumps(
            [
                card_payload(
                    "门户网站建设与新媒体运营服务公开招标公告",
                    source_column="bid",
                    notice_type="招标公告",
                    buyer="浙江某单位",
                    opportunity_class="A",
                    recommended_action="立即响应，下载采购文件并核对资格门槛、预算和投标截止时间。",
                ),
                card_payload(
                    "政务新媒体运营服务采购意向",
                    source_column="intention",
                    notice_type="采购意向公开",
                    buyer="杭州市某单位",
                    opportunity_class="B",
                    recommended_action="提前跟进，标记采购意向并准备需求沟通、案例材料和潜在方案。",
                ),
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cards = load_opportunity_cards(cards_path)
    focus_answer = answer_question_from_cards_file("今天有哪些 A/B 机会？", cards_path)
    bid_answer = answer_question_from_cards_file("招标公告中哪些需要立即响应？", cards_path)
    project_answer = answer_question("门户网站建设与新媒体运营服务公开招标公告为什么是 A？", cards)

    assert len(cards) == 2
    assert "A/B 机会" in focus_answer
    assert "门户网站建设与新媒体运营服务公开招标公告" in focus_answer
    assert "政务新媒体运营服务采购意向" in focus_answer
    assert "立即响应" in bid_answer
    assert "招标公告" in bid_answer
    assert "结论: A" in project_answer
    assert "浙江某单位" in project_answer
