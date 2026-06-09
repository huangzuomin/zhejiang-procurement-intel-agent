from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .models import NoticeLink


TARGET_MONITOR_URL = "https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement"
TARGET_DYNAMIC_LIST_ENDPOINT = "/magic/front/service/static/zcy.secondpagesearchlist.getSearchList/api"

DEFAULT_SOURCE_URLS = [
    TARGET_MONITOR_URL,
    "https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement701",
]


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attr_map = {key.lower(): value or "" for key, value in attrs}
        self._current = {
            "href": attr_map.get("href", ""),
            "title": attr_map.get("title", ""),
            "text": "",
        }

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current is not None:
            self.anchors.append(self._current)
            self._current = None


def fetch_text(url: str, *, timeout: int = 20) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; OpenClawProcurementIntel/0.1; +public-pages-only)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def parse_notice_links(html: str, base_url: str, *, limit: int = 20) -> list[NoticeLink]:
    parser = _AnchorParser()
    parser.feed(html)

    links: list[NoticeLink] = []
    seen_urls: set[str] = set()
    for anchor in parser.anchors:
        href = anchor["href"].strip()
        title = (anchor["title"] or anchor["text"]).strip()
        if not href or not title or not _looks_like_notice_link(href):
            continue

        absolute_url = urljoin(base_url, href)
        if absolute_url in seen_urls:
            continue
        links.append(NoticeLink(title=title, url=absolute_url))
        seen_urls.add(absolute_url)
        if len(links) >= limit:
            break
    return links


def fetch_public_notice_links(source_url: str, *, limit: int = 20, timeout: int = 20) -> list[NoticeLink]:
    html = fetch_text(source_url, timeout=timeout)
    return parse_notice_links(html, source_url, limit=limit)


def _looks_like_notice_link(href: str) -> bool:
    markers = [
        "zcyNotice_view",
        "articleId=",
        "/site/detail",
        "/project/",
        ".htm",
        ".html",
    ]
    ignored = ["javascript:", "#", "/site/home"]
    lower_href = href.lower()
    if any(lower_href.startswith(prefix) for prefix in ignored):
        return False
    return any(marker.lower() in lower_href for marker in markers)
