"""
Gemini API 기반 간식 이벤트 분류기.
"""

import os
import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        _client = genai.Client(api_key=api_key)
    return _client


def classify(notice: dict) -> dict:
    """
    공지사항이 간식 이벤트인지 판별.
    Returns: {"is_snack_event": bool, "reason": str}
    """
    title = notice.get("title", "")
    body = (notice.get("body", "") or "")[:600]

    prompt = f"""다음은 서울대학교 공지사항입니다.
이 공지사항이 무료 간식 나눔 행사인지 판별해주세요.

판별 기준:
- 학생들에게 무료로 음식/간식을 나눠주는 행사면 true
- 채용공고, 세미나, 식당 메뉴 안내, 복리후생 설명 등은 false
- 강연/행사의 부수적인 다과 제공도 false

제목: {title}
본문: {body}

반드시 아래 JSON 형식으로만 답하세요:
{{"is_snack_event": true또는false, "reason": "판별 이유 한 줄"}}"""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        text = response.text.strip()
        # 코드블록 제거
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini classify 오류: {e}")
        return {"is_snack_event": False, "reason": f"API 오류: {e}"}


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

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini extract_info 오류: {e}")
        return {
            "date": None, "time": None, "location": None,
            "description": title[:80], "organizer": None, "quantity": None,
        }


class Classifier:
    """runner.py와의 인터페이스 호환용 클래스."""

    def classify(self, notice: dict) -> dict:
        return classify(notice)

    def extract_info(self, notice: dict) -> dict:
        return extract_info(notice)
