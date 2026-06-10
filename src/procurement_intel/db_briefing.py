from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .storage import SQLiteStore


def build_brief_from_db(
    db_path: str | Path,
    *,
    today: str,
    mode: str,
    since_brief: str = "am",
    max_items: int = 10,
) -> str:
    store = SQLiteStore(db_path)
    if mode == "pm":
        cards = store.list_unpushed_focus_cards(today, pushed_mode=since_brief)
        all_cards = store.list_cards_for_date(today)
        counts = _counts(all_cards)
        lines = [
            f"浙江政采情报增量 {today}",
            "",
            f"概览: A {counts['A']} / B {counts['B']} / C {counts['C']} / D {counts['D']}",
            "",
        ]
        if not cards:
            lines.append("下午无新增重点机会。")
            lines.append("上午已推送的重点机会不重复展开。")
            return "\n".join(lines)
        lines.append("下午新增重点机会:")
        lines.extend(_render_cards(cards[:max_items]))
        hidden = len(cards) - max_items
        if hidden > 0:
            lines.append(f"另有 {hidden} 条新增重点已压缩。")
        return "\n".join(lines)

    cards = store.list_cards_for_date(today)
    counts = _counts(cards)
    focus_cards = [card for card in cards if card["opportunity_class"] in {"A", "B"}]
    lines = [
        f"浙江政采情报日报 {today}",
        "",
        f"概览: A {counts['A']} / B {counts['B']} / C {counts['C']} / D {counts['D']}",
        "",
    ]
    if not focus_cards:
        lines.append("今日无媒体/数字化重点机会。")
        return "\n".join(lines)
    lines.append("重点机会:")
    lines.extend(_render_cards(focus_cards[:max_items]))
    hidden = len(focus_cards) - max_items
    if hidden > 0:
        lines.append(f"另有 {hidden} 条重点机会已压缩。")
    return "\n".join(lines)


def _counts(cards: list[dict]) -> dict[str, int]:
    counter = Counter(card["opportunity_class"] for card in cards)
    return {key: counter.get(key, 0) for key in ["A", "B", "C", "D"]}


def _render_cards(cards: list[dict]) -> list[str]:
    lines: list[str] = []
    for index, card in enumerate(cards, start=1):
        lines.extend(
            [
                f"{index}. [{card['opportunity_class']}类] {card['title']}",
                f"   {card.get('buyer') or '采购人未披露'} / {_format_budget(card.get('budget'))}{_deadline_suffix(card)}",
                f"   匹配: {_reason_summary(card)}",
            ]
        )
    return lines


def _format_budget(value: float | None) -> str:
    if value is None:
        return "预算未披露"
    if value >= 10000:
        return f"{value / 10000:.1f}万元"
    return f"{value:.0f}元"


def _deadline_suffix(card: dict) -> str:
    return f" / 截止 {card['deadline']}" if card.get("deadline") else ""


def _reason_summary(card: dict) -> str:
    try:
        reasons = json.loads(card.get("reasons_json") or "[]")
    except json.JSONDecodeError:
        reasons = []
    return "、".join(reasons[:5]) if reasons else card.get("primary_category") or "需人工复核"
