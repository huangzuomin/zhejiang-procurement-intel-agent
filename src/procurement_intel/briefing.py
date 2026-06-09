from __future__ import annotations

from collections import defaultdict

from .models import OpportunityCard


def render_daily_brief(
    brief_date: str,
    cards: list[OpportunityCard],
    *,
    total_new_notices: int,
    max_items_per_class: int = 3,
) -> str:
    focus_cards = [card for card in cards if card.opportunity_class in {"A", "B"}]
    lines = [
        f"政采情报简报 {brief_date}",
        "",
        f"今日新增公告: {total_new_notices}",
        f"值得关注机会: {len(focus_cards)}",
        "",
    ]

    if not focus_cards:
        lines.extend(
            [
                "今日暂无 A/B 类重点机会。",
                "监测范围: 浙江政府采购公开公告。",
                "",
                "回复项目序号可继续追问。",
            ]
        )
        return "\n".join(lines)

    grouped: dict[str, list[OpportunityCard]] = defaultdict(list)
    for card in cards:
        grouped[card.opportunity_class].append(card)

    lines.extend(_render_class_section("A 类重点跟进", grouped["A"], max_items=max_items_per_class, preserve_all=True))
    lines.extend(_render_class_section("B 类值得关注", grouped["B"], max_items=max_items_per_class, preserve_all=False))

    low_priority_count = len([card for card in cards if card.opportunity_class in {"C", "D"}])
    if low_priority_count:
        lines.extend(["", f"C/D 类摘要: {low_priority_count} 个低优先级或排除项目"])

    lines.extend(["", "回复项目序号可继续追问。"])
    return "\n".join(line for line in lines if line is not None)


def render_column_daily_brief(
    brief_date: str,
    cards: list[OpportunityCard],
    *,
    quality_report: dict | None = None,
    max_items_per_section: int = 5,
) -> str:
    opportunity_counts = _opportunity_counts(cards)
    media_cards = [card for card in cards if card.classification.is_media_relevant]
    bid_cards = [card for card in cards if card.notice.source_column == "bid" and card.opportunity_class in {"A", "B", "C"}]
    intention_cards = [
        card for card in cards if card.notice.source_column == "intention" and card.opportunity_class in {"A", "B", "C"}
    ]
    risk_cards = [card for card in cards if card.risks or card.missing_fields]

    lines = [
        f"今日采购机会简报 {brief_date}",
        "",
        f"公告总数: {len(cards)}",
        f"机会分布: A {opportunity_counts['A']} / B {opportunity_counts['B']} / C {opportunity_counts['C']} / D {opportunity_counts['D']}",
        f"媒体/数字化相关项目: {len(media_cards)}",
    ]
    if quality_report:
        lines.extend(
            [
                f"采集质量: {quality_report.get('quality_grade', 'UNKNOWN')}",
                f"字段缺失: {quality_report.get('missing_field_counts', {})}",
            ]
        )

    lines.extend(_render_card_list("招标公告重点机会", bid_cards, max_items=max_items_per_section))
    lines.extend(_render_card_list("采购意向早期线索", intention_cards, max_items=max_items_per_section))
    lines.extend(_render_card_list("媒体/数字化相关机会", media_cards, max_items=max_items_per_section))
    lines.extend(_render_risk_section(risk_cards, max_items=max_items_per_section))

    return "\n".join(lines)


def _render_class_section(
    title: str,
    cards: list[OpportunityCard],
    *,
    max_items: int,
    preserve_all: bool,
) -> list[str]:
    if not cards:
        return []

    shown_cards = cards if preserve_all else cards[:max_items]
    lines = ["", title]
    for index, card in enumerate(shown_cards, start=1):
        risk_summary = "、".join(card.risks) if card.risks else "暂无明显风险"
        reason_summary = "、".join(card.reasons) if card.reasons else "需人工复核"
        lines.extend(
            [
                f"{index}. {card.notice.title}",
                f"   类别: {card.classification.primary_category}",
                f"   理由: {reason_summary}",
                f"   风险: {risk_summary}",
                f"   动作: {card.recommended_action}",
            ]
        )

    hidden_count = len(cards) - len(shown_cards)
    if hidden_count > 0:
        lines.append(f"   另有 {hidden_count} 个同类项目已压缩。")
    return lines


def _render_card_list(title: str, cards: list[OpportunityCard], *, max_items: int) -> list[str]:
    lines = ["", title]
    if not cards:
        lines.append("- 暂无")
        return lines

    shown_cards = cards[:max_items]
    for index, card in enumerate(shown_cards, start=1):
        lines.extend(
            [
                f"{index}. [{card.opportunity_class}] {card.notice.title}",
                f"   栏目: {card.notice.notice_type}",
                f"   采购人: {card.notice.buyer or '未知'}",
                f"   预算: {_format_budget(card.notice.budget)}",
                f"   截止/时间: {card.notice.deadline or '未披露'}",
                f"   分类: {card.classification.primary_category}",
                f"   动作: {card.recommended_action}",
            ]
        )
    hidden_count = len(cards) - len(shown_cards)
    if hidden_count > 0:
        lines.append(f"   另有 {hidden_count} 个项目已压缩。")
    return lines


def _render_risk_section(cards: list[OpportunityCard], *, max_items: int) -> list[str]:
    lines = ["", "字段缺失或风险提示"]
    if not cards:
        lines.append("- 暂无")
        return lines

    for card in cards[:max_items]:
        risks = "、".join(card.risks) if card.risks else "无"
        missing = "、".join(card.missing_fields) if card.missing_fields else "无"
        lines.append(f"- {card.notice.title}: 风险={risks}; 缺失={missing}")
    hidden_count = len(cards) - max_items
    if hidden_count > 0:
        lines.append(f"- 另有 {hidden_count} 个风险/缺失项已压缩。")
    return lines


def _opportunity_counts(cards: list[OpportunityCard]) -> dict[str, int]:
    return {key: len([card for card in cards if card.opportunity_class == key]) for key in ["A", "B", "C", "D"]}


def _format_budget(value: float | None) -> str:
    if value is None:
        return "未披露"
    if value >= 10000:
        return f"{value / 10000:.1f}万元"
    return f"{value:.0f}元"
