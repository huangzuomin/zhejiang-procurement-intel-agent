from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
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
            f"浙江政采情报增量｜{today}",
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
    a_cards = [card for card in cards if card["opportunity_class"] == "A"]
    b_cards = [card for card in cards if card["opportunity_class"] == "B"]
    focus_cards = a_cards + b_cards
    lines = [
        f"📋 浙江政采情报日报｜{today}",
        "",
        f"今日结论: {counts['A']} 个立即响应项目，{counts['B']} 个提前跟进线索。",
        f"概览: 采集 {len(cards)} 条｜A {counts['A']} / B {counts['B']} / C {counts['C']} / D {counts['D']}",
        "",
    ]
    if not focus_cards:
        lines.append("今日无媒体/数字化重点机会。")
        return "\n".join(lines)
    if a_cards:
        lines.append(f"🔴 A类｜立即响应｜{len(a_cards)}个")
        lines.extend(_render_cards(a_cards, label_prefix="A"))
        lines.append("")
    if b_cards:
        b_limit = min(max_items, 5)
        shown_b_cards = b_cards[:b_limit]
        lines.append(f"🟡 B类｜提前跟进｜{len(b_cards)}个，展示前{len(shown_b_cards)}个")
        lines.extend(_render_cards(shown_b_cards, label_prefix="B"))
        hidden = len(b_cards) - len(shown_b_cards)
        if hidden > 0:
            lines.append(f"另有 {hidden} 条 B 类线索已压缩。")
        lines.append("")
    lines.extend(_render_action_advice(counts))
    return "\n".join(lines)


def focus_notice_ids_for_brief(
    db_path: str | Path,
    *,
    today: str,
    mode: str,
    since_brief: str = "am",
    max_items: int = 10,
) -> list[int]:
    store = SQLiteStore(db_path)
    if mode == "pm":
        cards = store.list_unpushed_focus_cards(today, pushed_mode=since_brief)
    else:
        cards = [
            card
            for card in store.list_cards_for_date(today)
            if card["opportunity_class"] in {"A", "B"}
        ]
    return [int(card["notice_id"]) for card in cards[:max_items]]


def record_brief_push_success(
    db_path: str | Path,
    *,
    today: str,
    mode: str,
    since_brief: str = "am",
    max_items: int = 10,
    pushed_at: str | None = None,
) -> int:
    store = SQLiteStore(db_path)
    notice_ids = focus_notice_ids_for_brief(
        db_path,
        today=today,
        mode=mode,
        since_brief=since_brief,
        max_items=max_items,
    )
    timestamp = pushed_at or datetime.now(UTC).replace(microsecond=0).isoformat()
    for notice_id in notice_ids:
        store.record_push_event(
            notice_id=notice_id,
            brief_date=today,
            brief_mode=mode,
            status="success",
            pushed_at=timestamp,
        )
    return len(notice_ids)


def _counts(cards: list[dict]) -> dict[str, int]:
    counter = Counter(card["opportunity_class"] for card in cards)
    return {key: counter.get(key, 0) for key in ["A", "B", "C", "D"]}


def _render_cards(cards: list[dict], *, label_prefix: str | None = None) -> list[str]:
    lines: list[str] = []
    for index, card in enumerate(cards, start=1):
        label = f"{label_prefix}{index}" if label_prefix else f"{index}"
        lines.extend(
            [
                f"{label}｜{card['title']}",
                f"采购人: {card.get('buyer') or '未披露'}｜预算: {_format_budget(card.get('budget'))}{_deadline_suffix(card)}",
                f"匹配: {_reason_summary(card)}｜动作: {card.get('recommended_action') or '人工复核'}｜{_detail_link(card)}",
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
    return f"｜截止: {card['deadline']}" if card.get("deadline") else "｜截止: 未披露"


def _reason_summary(card: dict) -> str:
    try:
        reasons = json.loads(card.get("reasons_json") or "[]")
    except json.JSONDecodeError:
        reasons = []
    return "、".join(reasons[:5]) if reasons else card.get("primary_category") or "需人工复核"


def _detail_link(card: dict) -> str:
    url = str(card.get("detail_url") or "").replace(")", "%29")
    return f"[详情]({url})" if url else "详情未提供"


def _render_action_advice(counts: dict[str, int]) -> list[str]:
    lines = ["今日建议:"]
    if counts["A"]:
        lines.append("1. A类今天完成初筛: 确认资质、案例、预算和截止时间。")
    if counts["B"]:
        next_index = 2 if counts["A"] else 1
        lines.append(f"{next_index}. B类本周内提前建联: 准备案例包，确认需求范围。")
    low_priority_index = 1 + bool(counts["A"]) + bool(counts["B"])
    lines.append(f"{low_priority_index}. C/D 不展开，避免噪音；需要时再从数据库追查。")
    return lines
