from __future__ import annotations

from .models import ClassificationResult, Notice


CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "网站建设": ["门户网站建设", "网站建设", "专题页面", "内容管理", "CMS", "小程序"],
    "新媒体运营与运维": ["新媒体运营", "账号运营", "微信公众号", "视频号", "内容策划", "媒体投放"],
    "视频拍摄": ["宣传片", "专题片", "视频拍摄", "视频制作", "摄影摄像", "短视频", "剪辑", "后期制作"],
    "融媒体 / 传播服务": ["融媒体", "传播服务", "舆情监测", "媒资", "采编", "直播系统"],
    "GEO / AI 搜索优化 / 内容可发现性": ["GEO", "AI 搜索优化", "大模型搜索", "答案引擎优化", "内容可发现性"],
    "活动策划": ["活动策划", "展览展示", "文化创意", "品牌策划", "公关"],
    "广告制作": ["广告制作", "标识标牌", "喷绘", "展板", "海报", "灯箱", "宣传物料"],
    "信息化建设": ["信息化建设", "系统集成", "服务器", "网络设备", "机房改造"],
}

CORE_CATEGORIES = {
    "网站建设",
    "新媒体运营与运维",
    "视频拍摄",
    "融媒体 / 传播服务",
    "GEO / AI 搜索优化 / 内容可发现性",
}

EDGE_CATEGORIES = {"信息化建设", "活动策划", "广告制作"}


def classify_notice(notice: Notice) -> ClassificationResult:
    text = f"{notice.title}\n{notice.content}"
    matches = _match_categories(text)

    if not matches:
        return ClassificationResult(primary_category="无关项目", tier="excluded")

    primary_category = _select_primary(matches)
    secondary_categories = [category for category in matches if category != primary_category]
    evidence = matches[primary_category]

    if primary_category == "信息化建设" and not any(category in CORE_CATEGORIES for category in secondary_categories):
        return ClassificationResult(
            primary_category=primary_category,
            secondary_categories=secondary_categories,
            evidence=evidence,
            is_media_relevant=False,
            tier="edge",
            confidence="low",
        )

    tier = "core" if primary_category in CORE_CATEGORIES else "edge"
    confidence = "medium" if primary_category == "GEO / AI 搜索优化 / 内容可发现性" else "high"

    return ClassificationResult(
        primary_category=primary_category,
        secondary_categories=secondary_categories,
        evidence=evidence,
        is_media_relevant=True,
        tier=tier,
        confidence=confidence,
    )


def _match_categories(text: str) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        evidence = [keyword for keyword in keywords if keyword in text]
        if evidence:
            matches[category] = evidence
    return matches


def _select_primary(matches: dict[str, list[str]]) -> str:
    for category in CORE_CATEGORIES:
        if category in matches:
            return category
    for category in EDGE_CATEGORIES:
        if category in matches:
            return category
    return next(iter(matches))
