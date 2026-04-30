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
    # ── 본부 ──────────────────────────────────────────────
    {
        "name": "서울대학교 본부 공지",
        "url": "https://www.snu.ac.kr/snunow/notice/genernal",
        "type": "snu_main",
    },

    # ── 단과대 ────────────────────────────────────────────
    {
        "name": "인문대학",
        "url": "https://humanities.snu.ac.kr/community/notice",
        "type": "standard",
    },
    {
        "name": "사회과학대학",
        "url": "https://social.snu.ac.kr/공지사항/",
        "type": "standard",
    },
    {
        "name": "공과대학",
        "url": "https://eng.snu.ac.kr/snu/bbs/BMSR00004/list.do?menuNo=200176",
        "type": "snu_cms",
        "pagination_param": "pageIndex",
    },
    {
        "name": "자연과학대학",
        "url": "https://science.snu.ac.kr/news/announcement",
        "type": "standard",
    },
    {
        "name": "사범대학",
        "url": "https://edu.snu.ac.kr/category/board_17_gn_ldca7if5_20201130072915/",
        "type": "standard",
    },
    {
        "name": "경영대학",
        "url": "https://cba.snu.ac.kr/newsroom/notice",
        "type": "standard",
    },
    {
        "name": "농업생명과학대학",
        "url": "https://cals.snu.ac.kr/board/notice",
        "type": "standard",
    },
    {
        "name": "미술대학",
        "url": "https://art.snu.ac.kr/category/design/?catemenu=Notice&type=major",
        "type": "standard",
    },
    {
        "name": "음악대학",
        "url": "https://music.snu.ac.kr/notice",
        "type": "wordpress",
    },
    {
        "name": "법과대학",
        "url": "https://law.snu.ac.kr/board/notice",
        "type": "standard",
    },
    {
        "name": "간호대학",
        "url": "https://nursing.snu.ac.kr/board/notice",
        "type": "standard",
    },
    {
        "name": "약학대학",
        "url": "https://snupharm.snu.ac.kr/공지사항/",
        "type": "wordpress",
    },
    {
        "name": "수의과대학",
        "url": "https://vet.snu.ac.kr/category/board-3-BL-8Piv9u51-20211029154329/",
        "type": "standard",
    },
    {
        "name": "학부대학",
        "url": "https://snuc.snu.ac.kr/공지사항/",
        "type": "wordpress",
    },

    # ── 주요 학과/기관 ─────────────────────────────────────
    {
        "name": "기계공학부",
        "url": "https://me.snu.ac.kr/공통-공지사항/",
        "type": "wordpress",
    },
    {
        "name": "건축학과",
        "url": "https://architecture.snu.ac.kr/notice/",
        "type": "wordpress",
    },
    {
        "name": "생명과학부",
        "url": "https://biosci.snu.ac.kr/board/notice",
        "type": "standard",
    },
    {
        "name": "융합과학기술대학원",
        "url": "https://convergence.snu.ac.kr/bbs/board.php?bo_table=notice",
        "type": "gnuboard",
    },
    {
        "name": "컴퓨터공학부",
        "url": "https://cse.snu.ac.kr/community/notice",
        "type": "standard",
        "custom_selector": "ul.false li",
    },
    {
        "name": "산업공학과",
        "url": "https://ie.snu.ac.kr/notice/",
        "type": "wordpress",
    },
]
