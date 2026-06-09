from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import ClassificationResult, Notice, OpportunityCard


OUT_OF_SCOPE_TERMS = ["报名", "提交", "投标文件", "代办", "付款", "签合同", "合同签署"]


def load_opportunity_cards(json_path: str | Path) -> list[OpportunityCard]:
    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("opportunity cards JSON must be a list")
    return [_payload_to_card(item) for item in payload]


def answer_question_from_cards_file(question: str, json_path: str | Path) -> str:
    return answer_question(question, load_opportunity_cards(json_path))


def answer_question(question: str, cards: list[OpportunityCard]) -> str:
    if any(term in question for term in OUT_OF_SCOPE_TERMS):
        return "不能代办报名、提交投标文件或执行投标流程。可以帮你做情报研判、风险梳理和跟进清单。"

    list_answer = _answer_list_question(question, cards)
    if list_answer:
        return list_answer

    matches = _match_cards(question, cards)
    if len(matches) > 1:
        options = "\n".join(f"{index}. {card.notice.title}" for index, card in enumerate(matches, start=1))
        return f"找到多个可能项目，请指定序号或补充更具体标题：\n{options}"

    if not matches:
        return "没有在已采集机会卡中定位到该项目；我不会补编未采集事实。请提供项目标题、公告链接或简报序号。"

    return _render_card_answer(matches[0])


def _match_cards(question: str, cards: list[OpportunityCard]) -> list[OpportunityCard]:
    exact_matches = [card for card in cards if card.notice.title in question]
    if exact_matches:
        return exact_matches

    normalized_question = _normalize_text(question)
    phrase_matches = [
        card
        for card in cards
        if any(phrase in _normalize_text(card.notice.title) for phrase in _long_question_phrases(normalized_question))
    ]
    if phrase_matches:
        return phrase_matches

    keyword_matches = []
    for card in cards:
        searchable = "\n".join(
            [
                card.notice.title,
                card.notice.buyer or "",
                card.notice.notice_type,
                card.notice.source_column or "",
                card.opportunity_class,
            ]
        )
        if any(token and token in searchable for token in _question_tokens(question)):
            keyword_matches.append(card)
    return keyword_matches


def _question_tokens(question: str) -> list[str]:
    useful_terms = [
        "网站建设",
        "新媒体",
        "宣传片",
        "视频",
        "GEO",
        "信息化",
        "融媒体",
        "广告",
        "活动",
        "招标公告",
        "采购意向",
    ]
    return [term for term in useful_terms if term in question]


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+|[，。！？、：:；;（）()\\[\\]【】\\-/]", "", value)


def _long_question_phrases(normalized_question: str) -> list[str]:
    phrases: list[str] = []
    for size in range(min(16, len(normalized_question)), 5, -1):
        for start in range(0, len(normalized_question) - size + 1):
            phrase = normalized_question[start : start + size]
            if not re.search(r"[项目服务公告采购招标意向为什么是ABCD类级]+$", phrase):
                phrases.append(phrase)
    return phrases


def _answer_list_question(question: str, cards: list[OpportunityCard]) -> str | None:
    if any(term in question for term in ["为什么", "原因", "风险", "适合", "值得"]):
        return None

    if "立即响应" in question or ("招标公告" in question and ("哪些" in question or "机会" in question)):
        bid_cards = [card for card in cards if card.notice.source_column == "bid" and "立即" in card.recommended_action]
        return _render_card_list("招标公告中需要立即响应的项目", bid_cards)

    if "A/B" in question or "AB" in question or "重点机会" in question:
        focus_cards = [card for card in cards if card.opportunity_class in {"A", "B"}]
        return _render_card_list("A/B 机会", focus_cards)

    class_match = re.search(r"([ABCD])\s*[类级]?", question, re.IGNORECASE)
    if class_match and ("哪些" in question or "项目" in question or "机会" in question):
        opportunity_class = class_match.group(1).upper()
        class_cards = [card for card in cards if card.opportunity_class == opportunity_class]
        return _render_card_list(f"{opportunity_class} 类机会", class_cards)

    return None


def _render_card_list(title: str, cards: list[OpportunityCard]) -> str:
    if not cards:
        return f"{title}: 暂无。"
    lines = [title]
    for index, card in enumerate(cards, start=1):
        lines.append(
            f"{index}. [{card.opportunity_class}] {card.notice.title} | 栏目: {card.notice.notice_type} | 采购人: {card.notice.buyer or '未披露'} | 动作: {card.recommended_action}"
        )
    return "\n".join(lines)


def _render_card_answer(card: OpportunityCard) -> str:
    evidence = "、".join(card.classification.evidence) if card.classification.evidence else "未命中明确媒体业务证据"
    risks = "、".join(card.risks) if card.risks else "暂无明显风险"
    missing = "、".join(card.missing_fields) if card.missing_fields else "无"
    return "\n".join(
        [
            f"结论: {card.opportunity_class} 类，{card.notice.title}",
            f"栏目: {card.notice.notice_type}",
            f"采购人: {card.notice.buyer or '未披露'}",
            f"预算: {_format_optional(card.notice.budget)}",
            f"截止时间: {card.notice.deadline or '未披露'}",
            f"证据: {evidence}",
            f"风险: {risks}",
            f"建议: {card.recommended_action}",
            f"不确定项: {missing}",
            f"公告: {card.notice.url}",
        ]
    )


def _payload_to_card(item: dict[str, Any]) -> OpportunityCard:
    classification_payload = item.get("classification") or {}
    notice = Notice(
        title=str(item.get("title") or ""),
        url=str(item.get("detail_url") or item.get("url") or ""),
        notice_type=str(item.get("notice_type") or "公告"),
        publish_date=item.get("publish_date"),
        region=item.get("region"),
        buyer=item.get("buyer"),
        budget=item.get("budget"),
        deadline=item.get("deadline"),
        content=str(item.get("raw_detail_text") or item.get("content") or item.get("title") or ""),
        category_code=item.get("category_code"),
        source_column=item.get("source_column"),
        source_column_path=item.get("source_column_path"),
        source_category_code=item.get("source_category_code"),
    )
    classification = ClassificationResult(
        primary_category=str(classification_payload.get("primary_category") or "无关项目"),
        secondary_categories=list(classification_payload.get("secondary_categories") or []),
        evidence=list(classification_payload.get("evidence") or []),
        is_media_relevant=bool(classification_payload.get("is_media_relevant")),
        tier=str(classification_payload.get("tier") or "excluded"),
        confidence=str(classification_payload.get("confidence") or "low"),
    )
    return OpportunityCard(
        notice=notice,
        classification=classification,
        opportunity_class=str(item.get("opportunity_class") or "D"),
        reasons=list(item.get("reasons") or []),
        risks=list(item.get("risks") or []),
        recommended_action=str(item.get("recommended_action") or ""),
        missing_fields=list(item.get("missing_fields") or []),
    )


def _format_optional(value: float | None) -> str:
    if value is None:
        return "未披露"
    return str(value)
