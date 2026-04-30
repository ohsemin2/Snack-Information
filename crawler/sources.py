"""
SNU 각 사이트별 공지사항 파서.

각 파서는 get_notices(page) -> list[dict] 를 구현한다.
반환 형식:
  {
    "title": str,
    "url": str,        # 원문 링크 (절대 URL)
    "date": str,       # "2026-03-31" 형식이면 가장 좋지만, 원문 그대로도 OK
    "body": str | None # 본문 (상세 페이지 접근 후 채움)
  }
"""

import time
import hashlib
import re
from urllib.parse import urljoin, urlparse, urlencode, parse_qs, urlunparse


def _normalize_wp_url(url: str) -> str:
    """WordPress 페이지네이션 경로(/page/N/)를 제거해 article URL을 정규화한다."""
    return re.sub(r'/page/\d+/', '/', url)

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 15


def _get(url: str) -> BeautifulSoup | None:
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"[CRAWL ERROR] {url} — {e}")
        return None


def _absolute(base: str, href: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    return urljoin(base, href)


def _set_page_param(url: str, param: str, page: int) -> str:
    """URL 쿼리에서 특정 페이지 파라미터를 교체한다."""
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs[param] = [str(page)]
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    return urlunparse(parsed._replace(query=new_query))


def fetch_body(url: str) -> str:
    """상세 페이지에서 본문 텍스트를 추출한다."""
    soup = _get(url)
    if not soup:
        return ""
    # 공통 본문 후보 선택자 (넓은 범위 → 좁은 범위 순)
    for selector in [
        ".board-view-content", ".bbs-view-content", ".view-content",
        ".board_view", ".content-area", "article", ".post-content",
        "#bo_v_con", ".xe_content",  # 그누보드/XE
        ".view_con", ".detail_con",
    ]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(separator="\n", strip=True)
    # 폴백: <main> 또는 <body>에서 스크립트/네비 제거 후 텍스트
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    main = soup.find("main") or soup.find("body")
    return main.get_text(separator="\n", strip=True)[:3000] if main else ""


# ─────────────────────────────────────────────
# 파서 클래스들
# ─────────────────────────────────────────────

class StandardParser:
    """
    SNU 표준 CMS 형식.
    테이블: <table class="board-list"> 또는 <ul class="board-list">
    페이지네이션: ?page=N
    """

    def __init__(self, source: dict):
        self.source = source
        self.base_url = source["url"]

    def get_notices(self, page: int = 1) -> list[dict]:
        url = _set_page_param(self.base_url, "page", page)
        soup = _get(url)
        if not soup:
            return []

        notices = []
        # 후보 선택자들
        custom_selector = self.source.get("custom_selector")
        rows = (
            soup.select(custom_selector) if custom_selector
            else (
                soup.select("table.board-list tbody tr")
                or soup.select("table tbody tr")
                or soup.select("ul.board-list li")
                or soup.select(".bbs-list li")
                or soup.select(".notice-list li")
            )
        )

        for row in rows:
            a_tag = row.find("a")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = _absolute(self.base_url, a_tag.get("href", ""))
            if not title or not href:
                continue

            # 날짜: td/span에서 yyyy-mm-dd 또는 yyyy.mm.dd 패턴 탐색
            date_text = ""
            date_el = row.select_one(".date, .td_date, [class*='date'], td:last-child")
            if date_el:
                date_text = date_el.get_text(strip=True)

            notices.append({
                "title": title,
                "url": href,
                "date": date_text,
                "body": None,
                "source_name": self.source["name"],
            })

        return notices


class SnuMainParser:
    """서울대학교 본부 공지사항 (snu.ac.kr)."""

    def __init__(self, source: dict):
        self.source = source
        self.base_url = source["url"]

    def get_notices(self, page: int = 1) -> list[dict]:
        url = _set_page_param(self.base_url, "page", page)
        soup = _get(url)
        if not soup:
            return []

        notices = []
        for item in soup.select(".board-list-wrap li, .bbs-list tr, tr"):
            a_tag = item.find("a")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = _absolute("https://www.snu.ac.kr", a_tag.get("href", ""))
            if not title or "snu.ac.kr" not in href:
                continue
            date_el = item.select_one(".date, [class*='date'], td:last-child, span.date")
            date_text = date_el.get_text(strip=True) if date_el else ""
            notices.append({
                "title": title,
                "url": href,
                "date": date_text,
                "body": None,
                "source_name": self.source["name"],
            })

        return notices


class SnuCmsParser:
    """
    SNU JSP CMS (.do 형식, eng.snu.ac.kr 등).
    페이지네이션: pageIndex=N
    """

    def __init__(self, source: dict):
        self.source = source
        self.base_url = source["url"]
        self.page_param = source.get("pagination_param", "pageIndex")

    def get_notices(self, page: int = 1) -> list[dict]:
        url = _set_page_param(self.base_url, self.page_param, page)
        soup = _get(url)
        if not soup:
            return []

        notices = []
        origin = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(self.base_url))
        for row in soup.select("table tbody tr, .bbs-list tr"):
            a_tag = row.find("a")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = _absolute(origin, a_tag.get("href", ""))
            if not title or not href:
                continue
            tds = row.find_all("td")
            date_text = tds[-1].get_text(strip=True) if tds else ""
            notices.append({
                "title": title,
                "url": href,
                "date": date_text,
                "body": None,
                "source_name": self.source["name"],
            })

        return notices


class WordPressParser:
    """
    WordPress 기반 공지사항 (음대, 건축학과, 학부대학 등).
    페이지네이션: ?paged=N 또는 /page/N/
    """

    def __init__(self, source: dict):
        self.source = source
        self.base_url = source["url"]

    def get_notices(self, page: int = 1) -> list[dict]:
        if page == 1:
            url = self.base_url
        else:
            # /page/N/ 형식 시도
            base = self.base_url.rstrip("/")
            url = f"{base}/page/{page}/"

        soup = _get(url)
        if not soup:
            return []

        notices = []
        seen_urls = set()
        for item in soup.select("article, .post, li.notice, .entry, .bbs_list li"):
            a_tag = item.find("a")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = _normalize_wp_url(_absolute(self.base_url, a_tag.get("href", "")))
            if not title or not href or href in seen_urls:
                continue
            seen_urls.add(href)
            date_el = item.select_one("time, .date, .published, [class*='date']")
            date_text = ""
            if date_el:
                date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)
            notices.append({
                "title": title,
                "url": href,
                "date": date_text,
                "body": None,
                "source_name": self.source["name"],
            })

        return notices


class GnuBoardParser:
    """
    그누보드 기반 공지사항 (convergence.snu.ac.kr 등).
    페이지네이션: &page=N
    """

    def __init__(self, source: dict):
        self.source = source
        self.base_url = source["url"]
        origin_parsed = urlparse(self.base_url)
        self.origin = f"{origin_parsed.scheme}://{origin_parsed.netloc}"

    def get_notices(self, page: int = 1) -> list[dict]:
        url = self.base_url + f"&page={page}" if page > 1 else self.base_url
        soup = _get(url)
        if not soup:
            return []

        notices = []
        for row in soup.select("#bo_list tbody tr, .bo_list tr"):
            a_tag = row.select_one(".bo_tit a, td.td_subject a")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = _absolute(self.origin, a_tag.get("href", ""))
            if not title or not href:
                continue
            date_el = row.select_one(".td_datetime, .td_date, td:last-child")
            date_text = date_el.get_text(strip=True) if date_el else ""
            notices.append({
                "title": title,
                "url": href,
                "date": date_text,
                "body": None,
                "source_name": self.source["name"],
            })

        return notices


# ─────────────────────────────────────────────
# 파서 팩토리
# ─────────────────────────────────────────────

def get_parser(source: dict):
    t = source.get("type", "standard")
    if t == "snu_main":
        return SnuMainParser(source)
    elif t == "snu_cms":
        return SnuCmsParser(source)
    elif t == "wordpress":
        return WordPressParser(source)
    elif t == "gnuboard":
        return GnuBoardParser(source)
    else:
        return StandardParser(source)
