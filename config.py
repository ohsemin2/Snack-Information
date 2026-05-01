import os
from dotenv import load_dotenv

load_dotenv()

# 크롤링 간격 (초)
CRAWL_INTERVAL_SECONDS = 86400  # 1일

# 요청 간 딜레이 (초) — 서버 부하 방지
REQUEST_DELAY = 1.5

# Groq API 호출 간 딜레이 (초) — 분당 30 RPM 제한 대응
GROQ_DELAY = 2.5

# 각 공지사항 최대 페이지 수 (초과 시 중단)
MAX_PAGES_PER_SOURCE = 5

# 공지사항 소스 목록
# type: "standard" (공통 SNU CMS), "wordpress", "custom"
SOURCES = [
    # ── 주요 학과/기관 ─────────────────────────────────────
    {
        "name": "산업공학과",
        "url": "https://ie.snu.ac.kr/notice/",
        "type": "wordpress",
    },
    {
        "name": "컴퓨터공학부",
        "url": "https://cse.snu.ac.kr/community/notice",
        "type": "standard",
        "custom_selector": 'ul[class="false"] li',
    },
    {
        "name": "생명과학부",
        "url": "https://biosci.snu.ac.kr/board/notice",
        "type": "standard",
    },
    {
        "name": "기계공학부",
        "url": "https://me.snu.ac.kr/공통-공지사항/",
        "type": "wordpress",
    },

    # ── 단과대 ────────────────────────────────────────────
    {
        "name": "학부대학",
        "url": "https://snuc.snu.ac.kr/공지사항/",
        "type": "wordpress",
    },
    {
        "name": "약학대학",
        "url": "https://snupharm.snu.ac.kr/공지사항/",
        "type": "wordpress",
    },
    {
        "name": "간호대학",
        "url": "https://nursing.snu.ac.kr/board/notice",
        "type": "standard",
    },
    {
        "name": "음악대학",
        "url": "https://music.snu.ac.kr/notice",
        "type": "wordpress",
        "custom_selector": "li.pa_subject",
    },
    {
        "name": "미술대학",
        "url": "https://art.snu.ac.kr/category/design/?catemenu=Notice&type=major",
        "type": "standard",
    },
    {
        "name": "농업생명과학대학",
        "url": "https://cals.snu.ac.kr/board/notice",
        "type": "standard",
    },
    {
        "name": "경영대학",
        "url": "https://cba.snu.ac.kr/newsroom/notice",
        "type": "standard",
    },
    {
        "name": "자연과학대학",
        "url": "https://science.snu.ac.kr/news/announcement",
        "type": "standard",
    },
    {
        "name": "공과대학",
        "url": "https://eng.snu.ac.kr/snu/bbs/BMSR00004/list.do?menuNo=200176",
        "type": "snu_cms",
        "pagination_param": "pageIndex",
    },
    {
        "name": "사회과학대학",
        "url": "https://social.snu.ac.kr/공지사항/",
        "type": "wordpress",
    },
    {
        "name": "인문대학",
        "url": "https://humanities.snu.ac.kr/community/notice",
        "type": "standard",
    },

    # ── 본부 ──────────────────────────────────────────────
    {
        "name": "서울대학교 본부 공지",
        "url": "https://www.snu.ac.kr/snunow/notice/genernal",
        "type": "snu_main",
    },
]
