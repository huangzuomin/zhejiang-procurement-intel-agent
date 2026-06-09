from __future__ import annotations

import re
from html.parser import HTMLParser

from .models import Notice


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored_tag_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._ignored_tag_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._ignored_tag_depth:
            self._ignored_tag_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_tag_depth:
            return
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return " ".join(self.parts)


def parse_notice_detail(
    html: str,
    *,
    url: str,
    fallback_title: str | None = None,
    notice_type: str = "公告",
    region: str | None = "浙江",
) -> Notice:
    content = _extract_text(html)
    title = _extract_title(html) or fallback_title or _compact(content)[:120]
    publish_date = _extract_publish_date(html, content)
    buyer = _extract_buyer(content)
    budget = _parse_budget(content)
    deadline = _extract_deadline(content)

    return Notice(
        title=title,
        url=url,
        notice_type=notice_type,
        publish_date=publish_date,
        region=region,
        buyer=buyer,
        budget=budget,
        deadline=deadline,
        content=content[:8000],
        category_code=None,
    )


def _extract_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return _compact(parser.text())


def _extract_title(html: str) -> str | None:
    patterns = [
        r"<h1[^>]*>(.*?)</h1>",
        r"<h2[^>]*>(.*?)</h2>",
        r"<title[^>]*>(.*?)</title>",
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            return _compact(re.sub(r"<[^>]+>", " ", match.group(1)))[:200]
    return None


def _extract_publish_date(html: str, content: str) -> str | None:
    meta_match = re.search(r'<meta[^>]+name=["\']PubDate["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if meta_match:
        date_match = re.search(r"\d{4}-\d{1,2}-\d{1,2}", meta_match.group(1))
        if date_match:
            return _normalize_date(date_match.group(0))

    text_match = re.search(r"(?:发布时间|发布日期|公告日期)[:：]?\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2})", content)
    if text_match:
        return _normalize_date(text_match.group(1))
    return None


def _extract_buyer(content: str) -> str | None:
    patterns = [
        r"采购人信息\s*名称[:：]\s*([^\s，,。；;]+)",
        r"采购人[:：]\s*([^\s，,。；;]+)",
        r"采购单位[:：]\s*([^\s，,。；;]+)",
        r"采购单位\s+(.+?)(?=\s+采购项目名称|\s+预算金额|\s+采购需求|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip(" ：:")
    return None


def _parse_budget(content: str) -> float | None:
    patterns = [
        r"(?:预算金额|预算|最高限价)[^。；;\n]{0,20}?([\d,.]+)\s*万元",
        r"(?:预算金额|预算|最高限价)[^。；;\n]{0,20}?([\d,.]+)\s*元",
        r"(?:预算金额|预算|最高限价)\s*[（(]\s*元\s*[）)]\s*[:：]?\s*([\d,.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if not match:
            continue
        amount = float(match.group(1).replace(",", ""))
        if "万元" in match.group(0):
            amount *= 10000
        return amount
    return None


def _extract_deadline(content: str) -> str | None:
    patterns = [
        r"(?:提交投标文件截止时间|响应文件提交截止时间|开标时间|截止时间)[^。；;\n]{0,30}?(\d{4}年\d{1,2}月\d{1,2}日)",
        r"(?:提交投标文件截止时间|响应文件提交截止时间|开标时间|截止时间)[^。；;\n]{0,30}?(\d{4}-\d{1,2}-\d{1,2})",
        r"于\s*(\d{4}年\d{1,2}月\d{1,2}日)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return _normalize_date(match.group(1))
    return None


def _normalize_date(value: str) -> str:
    numbers = re.findall(r"\d+", value)
    if len(numbers) < 3:
        return value
    return f"{int(numbers[0]):04d}-{int(numbers[1]):02d}-{int(numbers[2]):02d}"


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
