"""
Groq API 기반 간식 이벤트 분류기.
"""

import os
import json
import logging
from groq import Groq

logger = logging.getLogger(__name__)

CURRENT_MODEL = "llama-3.3-70b-versatile"

CLASSIFY_SYSTEM_PROMPT = """당신은 서울대학교 공지사항이 캠퍼스 내 무료 간식 나눔 이벤트인지 판별하는 전문가입니다.

[TRUE로 판별해야 하는 경우]
행사 목적에 무관하게, 현장에서 무료로 음식/음료/간식을 배포하는 내용이 있으면 true.
예: 시험기간 간식 이벤트, 커피차 방문, 선착순 간식 증정, 취업설명회에서 간식 제공, 개강 행사 음료 나눔

[FALSE로 판별해야 하는 경우]
- 기업 채용공고에서 입사 후 복리후생으로 제공되는 간식/식대 언급
- 식당 메뉴 안내, 영양 정보
- 행사 내용에 간식 제공 언급이 전혀 없는 경우

[핵심 원칙]
- 현장에서 나눠준다는 내용이 조금이라도 있으면 true
- 불확실하면 true로 판단 (놓치는 것이 더 나쁨)

반드시 아래 JSON 형식으로만 답하세요:
{"is_snack_event": true 또는 false, "reason": "판별 이유 한 줄"}"""

_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY 환경변수가 설정되지 않았습니다.")
        _client = Groq(api_key=api_key)
    return _client


def classify(notice: dict) -> dict:
    """
    공지사항이 간식 이벤트인지 판별.
    Returns: {"is_snack_event": bool, "reason": str}
    """
    title = notice.get("title", "")
    body = (notice.get("body", "") or "")[:300]

    client = _get_client()
    response = client.chat.completions.create(
        model=CURRENT_MODEL,
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
            {"role": "user", "content": f"제목: {title}\n본문: {body}"},
        ],
        temperature=0,
        response_format={"type": "json_object"},
        max_tokens=100,
    )
    return json.loads(response.choices[0].message.content)


def extract_info(notice: dict) -> dict:
    """
    간식 이벤트로 판별된 공지사항에서 구조화된 정보를 추출.
    Returns: {date, time, location, description, organizer, quantity}
    """
    title = notice.get("title", "")
    body = (notice.get("body", "") or "")[:2000]

    prompt = f"""다음 서울대학교 간식 나눔 공지사항에서 정보를 추출해주세요.

제목: {title}
본문: {body}

반드시 아래 JSON 형식으로만 답하세요 (없는 정보는 null):
{{
  "date": "YYYY-MM-DD 형식, 없으면 null",
  "time": "HH:MM~HH:MM 형식, 없으면 null",
  "location": "장소명, 없으면 null",
  "description": "간식 종류와 행사 내용 한 줄 요약",
  "organizer": "주최 단체명, 없으면 null",
  "quantity": "수량 또는 선착순 인원, 없으면 null"
}}"""

    client = _get_client()
    response = client.chat.completions.create(
        model=CURRENT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


class Classifier:
    """runner.py와의 인터페이스 호환용 클래스."""

    def classify(self, notice: dict) -> dict:
        return classify(notice)

    def extract_info(self, notice: dict) -> dict:
        return extract_info(notice)
