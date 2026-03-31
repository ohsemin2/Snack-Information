"""
규칙 기반 간식 이벤트 분류기.
Claude API 없이 키워드 매칭 + 정규식으로 동작한다.
"""

import re
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# ─── 간식 이벤트 판별 키워드 ────────────────────────────────

# 이 중 하나 이상 포함 → 간식 이벤트 후보
SNACK_KEYWORDS = [
    "간식", "나눔", "무료 배포", "무료배포", "선착순", "증정",
    "붕어빵", "떡볶이", "호떡", "핫도그", "핫초코", "핫코코아",
    "커피", "아메리카노", "라떼", "음료", "주스", "버블티",
    "케이크", "컵케이크", "마카롱", "쿠키", "도넛", "도너츠",
    "빵", "샌드위치", "와플", "팬케이크",
    "아이스크림", "아이스바", "젤라토",
    "과자", "사탕", "젤리", "초코", "초콜릿",
    "떡", "약과", "한과", "찹쌀",
    "피자", "치킨", "햄버거", "라면", "김밥", "떡볶이",
    "포도", "귤", "과일", "딸기",
    "다과", "간식거리", "먹거리",
]

# 이 키워드가 제목/본문에 있고 → 간식 언급이 부수적일 가능성 (감점)
NEGATIVE_KEYWORDS = [
    "채용", "인턴", "취업", "공채", "모집공고", "채용공고",
    "복리후생", "복지혜택", "급여",
    "영업시간", "영업 시간", "메뉴", "식단표",
]

# 이벤트성 키워드 (있으면 가중치 추가)
EVENT_KEYWORDS = ["행사", "이벤트", "파티", "축제", "기념", "환영", "오픈"]


def _text(notice: dict) -> str:
    """제목 + 본문을 합친 전체 텍스트."""
    return (notice.get("title", "") + "\n" + (notice.get("body", "") or "")).lower()


def classify(notice: dict) -> dict:
    """
    공지사항이 간식 이벤트인지 판별.
    Returns: {"is_snack_event": bool, "reason": str}
    """
    title = notice.get("title", "")
    text = _text(notice)

    # 부정 키워드 우선 체크 (채용공고 등)
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            return {"is_snack_event": False, "reason": f"부정 키워드 감지: '{kw}'"}

    # 간식 키워드 매칭
    matched = [kw for kw in SNACK_KEYWORDS if kw in text]
    if not matched:
        return {"is_snack_event": False, "reason": "간식 관련 키워드 없음"}

    # "무료" 또는 "나눔" 또는 "선착순" 없이 음식 단어만 있으면
    # 식당 메뉴 공지일 수 있음 → 이벤트성 키워드도 없으면 제외
    free_hint = any(kw in text for kw in ["무료", "나눔", "선착순", "증정", "공짜", "드립니다", "드려요", "제공"])
    event_hint = any(kw in text for kw in EVENT_KEYWORDS)

    if not free_hint and not event_hint:
        return {"is_snack_event": False, "reason": f"음식 키워드만 있고 무료 나눔 맥락 없음 (매칭: {matched[:2]})"}

    reason = f"간식 키워드 매칭: {matched[:3]}"
    return {"is_snack_event": True, "reason": reason}


# ─── 정보 추출 ───────────────────────────────────────────────

# 날짜 패턴들
_DATE_PATTERNS = [
    # 2026-03-31 / 2026.03.31 / 2026/03/31
    (re.compile(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})"), "ymd"),
    # 3월 31일 / 3.31 / 3/31 (연도 없음 → 올해로 처리)
    (re.compile(r"(\d{1,2})월\s*(\d{1,2})일"), "md"),
    (re.compile(r"(\d{1,2})[./](\d{1,2})(?!\d)"), "md"),
]

# 시간 패턴들
_TIME_PATTERNS = [
    # 11:00~13:00 / 11:00-13:00
    re.compile(r"(\d{1,2}:\d{2})\s*[~\-~–]\s*(\d{1,2}:\d{2})"),
    # 11시~13시 / 오전 11시~오후 1시
    re.compile(r"(?:오전|오후)?\s*(\d{1,2})시\s*[~\-]\s*(?:오전|오후)?\s*(\d{1,2})시"),
    # 단독 시각: 11:00 / 오후 3시
    re.compile(r"(\d{1,2}:\d{2})"),
    re.compile(r"(?:오전|오후)\s*(\d{1,2})시"),
]

# 장소 패턴 (SNU 건물·공간 특화)
_LOCATION_PATTERNS = [
    # "아크로 광장", "학생회관 앞", "공대 로비" 등
    re.compile(r"([가-힣a-zA-Z\d]+\s*(?:관|홀|광장|로비|앞|앞쪽|옆|층|호|루|캠퍼스|플라자|마당|정문|후문))"),
    # 특정 건물명
    re.compile(r"(아크로|두레|기숙사|학생회관|학관|자하연|220동|301동|\d{3}동\s*\d+호?)"),
]

# 음식 키워드 → 표시용 이름 매핑
_FOOD_MAP = {
    "붕어빵": "붕어빵", "떡볶이": "떡볶이", "호떡": "호떡", "핫도그": "핫도그",
    "커피": "커피", "아메리카노": "아메리카노", "라떼": "라떼", "음료": "음료",
    "케이크": "케이크", "컵케이크": "컵케이크", "마카롱": "마카롱", "쿠키": "쿠키",
    "도넛": "도넛", "도너츠": "도넛", "빵": "빵", "샌드위치": "샌드위치",
    "아이스크림": "아이스크림", "과자": "과자", "사탕": "사탕",
    "초코": "초콜릿", "초콜릿": "초콜릿", "떡": "떡", "다과": "다과",
    "피자": "피자", "치킨": "치킨", "과일": "과일", "귤": "귤",
    "포도": "포도", "딸기": "딸기", "주스": "주스", "핫초코": "핫초코",
    "와플": "와플", "팬케이크": "팬케이크", "버블티": "버블티",
}

# 수량 패턴
_QUANTITY_PATTERNS = [
    re.compile(r"선착순\s*(\d+)\s*(?:명|분)"),
    re.compile(r"(\d+)\s*(?:명|분)\s*선착순"),
    re.compile(r"(\d+)\s*(?:개|인분|봉지|컵|잔)"),
    re.compile(r"총\s*(\d+)\s*(?:명|개|개분)"),
]


def _extract_date(text: str) -> str | None:
    today = date.today()

    for pattern, fmt in _DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        try:
            if fmt == "ymd":
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                return f"{y:04d}-{mo:02d}-{d:02d}"
            elif fmt == "md":
                mo, d = int(m.group(1)), int(m.group(2))
                # 올해 혹은 내년 결정 (이미 지난 날짜면 내년)
                y = today.year
                candidate = date(y, mo, d)
                if candidate < today - timedelta(days=7):
                    candidate = date(y + 1, mo, d)
                return candidate.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # "오늘" / "내일"
    if "오늘" in text:
        return today.strftime("%Y-%m-%d")
    if "내일" in text:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    return None


def _extract_time(text: str) -> str | None:
    # 범위 패턴 우선
    m = _TIME_PATTERNS[0].search(text)
    if m:
        return f"{m.group(1)}~{m.group(2)}"

    m = _TIME_PATTERNS[1].search(text)
    if m:
        return f"{m.group(1)}시~{m.group(2)}시"

    m = _TIME_PATTERNS[2].search(text)
    if m:
        return m.group(1)

    m = _TIME_PATTERNS[3].search(text)
    if m:
        return m.group(0).strip()

    return None


def _extract_location(text: str) -> str | None:
    for pattern in _LOCATION_PATTERNS:
        m = pattern.search(text)
        if m:
            loc = m.group(1).strip()
            if len(loc) >= 2:
                return loc
    return None


def _extract_foods(text: str) -> list[str]:
    found = []
    for kw, label in _FOOD_MAP.items():
        if kw in text and label not in found:
            found.append(label)
    return found


def _extract_quantity(text: str) -> str | None:
    for pattern in _QUANTITY_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(0).strip()
    return None


def extract_info(notice: dict) -> dict:
    """
    간식 이벤트로 판별된 공지사항에서 구조화된 정보를 추출.
    Returns: {date, time, location, description, organizer, quantity}
    """
    title = notice.get("title", "")
    body = notice.get("body", "") or ""
    full_text = title + "\n" + body

    event_date = _extract_date(full_text)
    event_time = _extract_time(full_text)
    location = _extract_location(full_text)
    foods = _extract_foods(full_text.lower())
    quantity = _extract_quantity(full_text)

    # description: "음식종류 무료 나눔" 형식으로 조합
    if foods:
        description = f"{', '.join(foods[:3])} 무료 나눔"
    else:
        description = title[:80]

    return {
        "date": event_date,
        "time": event_time,
        "location": location,
        "description": description,
        "organizer": None,   # 규칙으로 추출 어려움 — source_name으로 대체
        "quantity": quantity,
    }


class Classifier:
    """기존 claude_client.Classifier와 동일한 인터페이스."""

    def classify(self, notice: dict) -> dict:
        return classify(notice)

    def extract_info(self, notice: dict) -> dict:
        return extract_info(notice)
