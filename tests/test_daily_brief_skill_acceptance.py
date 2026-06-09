from pathlib import Path

from procurement_intel.daily_pipeline import run_daily_pipeline
from procurement_intel.qa import answer_question_from_cards_file


ROOT = Path(__file__).resolve().parents[1]
REAL_SAMPLE = ROOT / "tests/fixtures/zfcg_browser_two_columns_60.json"


def test_daily_brief_skill_acceptance_uses_real_two_column_sample(tmp_path) -> None:
    result = run_daily_pipeline(REAL_SAMPLE, output_dir=tmp_path / "daily-sample", today="2026-06-09")

    assert result.quality_report["quality_grade"] == "PASS"
    assert result.quality_report["category_counts"] == {"采购意向公开": 30, "招标公告": 30}
    assert "机会分布: A" in result.daily_brief
    assert "招标公告重点机会" in result.daily_brief
    assert "采购意向早期线索" in result.daily_brief
    assert "媒体/数字化相关机会" in result.daily_brief
    assert "立即响应" in result.daily_brief
    assert "提前跟进" in result.daily_brief

    focus_answer = answer_question_from_cards_file("今天有哪些 A/B 机会？", result.paths["opportunity_cards"])
    project_answer = answer_question_from_cards_file(
        "嘉兴市主城区（南湖区）旅游标识标牌提升项目为什么是 A？",
        result.paths["opportunity_cards"],
    )
    immediate_answer = answer_question_from_cards_file("招标公告中哪些需要立即响应？", result.paths["opportunity_cards"])

    assert "A/B 机会" in focus_answer
    assert "旅游标识标牌提升项目" in project_answer
    assert "结论: A" in project_answer
    assert "立即响应" in immediate_answer
