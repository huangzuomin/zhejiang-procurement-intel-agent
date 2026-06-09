from __future__ import annotations

from datetime import date

from .models import ClassificationResult, Notice, OpportunityCard


LOW_BUDGET_THRESHOLD = 50000
URGENT_DAYS = 3


def score_notice(notice: Notice, classification: ClassificationResult, *, today: str | None = None) -> OpportunityCard:
    reasons: list[str] = []
    risks: list[str] = []
    missing_fields = _missing_fields(notice)

    if missing_fields:
        risks.append("信息不足")

    if notice.budget is not None and notice.budget < LOW_BUDGET_THRESHOLD:
        risks.append("预算过低")

    if _is_urgent(notice.deadline, today):
        risks.append("截止临期")

    if classification.tier == "excluded":
        risks.append("无媒体业务匹配证据")
        return OpportunityCard(
            notice=notice,
            classification=classification,
            opportunity_class="D",
            reasons=[],
            risks=_dedupe(risks),
            recommended_action="排除，不进入业务跟进清单。",
            missing_fields=missing_fields,
        )

    if not classification.is_media_relevant:
        risks.append("媒体相关证据不足")
        return OpportunityCard(
            notice=notice,
            classification=classification,
            opportunity_class="C",
            reasons=["仅作为边缘机会留存，需人工筛查是否包含媒体业务子项。"],
            risks=_dedupe(risks),
            recommended_action="低优先级查看采购文件，确认是否存在网站、内容、传播或运营子项。",
            missing_fields=missing_fields,
        )

    reasons.append("媒体业务匹配明确")

    if classification.primary_category == "GEO / AI 搜索优化 / 内容可发现性":
        reasons.append("GEO 类机会需保守研判")
        opportunity_class = "B"
    elif risks:
        opportunity_class = "B"
    else:
        opportunity_class = "A"

    action = _recommended_action(notice, opportunity_class)

    return OpportunityCard(
        notice=notice,
        classification=classification,
        opportunity_class=opportunity_class,
        reasons=reasons,
        risks=_dedupe(risks),
        recommended_action=action,
        missing_fields=missing_fields,
    )


def _missing_fields(notice: Notice) -> list[str]:
    missing = []
    if notice.budget is None:
        missing.append("budget")
    if not notice.deadline:
        missing.append("deadline")
    return missing


def _is_urgent(deadline: str | None, today: str | None) -> bool:
    if not deadline or not today:
        return False
    try:
        deadline_date = date.fromisoformat(deadline)
        today_date = date.fromisoformat(today)
    except ValueError:
        return False
    return 0 <= (deadline_date - today_date).days <= URGENT_DAYS


def _recommended_action(notice: Notice, opportunity_class: str) -> str:
    if notice.source_column == "bid":
        if opportunity_class == "A":
            return "立即响应，下载采购文件并核对资格门槛、预算和投标截止时间。"
        return "立即核对采购文件，确认媒体相关子项、预算和响应窗口。"
    if notice.source_column == "intention":
        return "提前跟进，标记采购意向并准备需求沟通、案例材料和潜在方案。"
    return "重点跟进，确认采购文件、资格门槛和响应窗口。" if opportunity_class == "A" else "值得关注，先核对需求边界、预算和截止时间。"


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
