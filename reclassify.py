"""
기존 is_snack_event=False 데이터를 새 모델로 일괄 재분류하는 단발성 스크립트.
Supabase migration 후 한 번만 실행.

사용법:
    python reclassify.py
"""

import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

from database import SessionLocal
from models import Event
from crawler.sources import fetch_body
from classifier.rule_classifier import classify, extract_info, CURRENT_MODEL
from config import REQUEST_DELAY, GROQ_DELAY


def main():
    db = SessionLocal()
    try:
        targets = (
            db.query(Event)
            .filter(Event.is_snack_event == False)
            .filter(Event.classified_by != CURRENT_MODEL)
            .all()
        )
        logger.info(f"재분류 대상: {len(targets)}건")

        reclassified = 0
        upgraded = 0

        for event in targets:
            logger.info(f"  처리 중: {event.title}")

            # 본문이 없으면 다시 가져오기
            body = event.raw_body or ""
            if not body:
                time.sleep(REQUEST_DELAY)
                body = fetch_body(event.source_url)
                event.raw_body = body[:5000]

            notice = {
                "title": event.title,
                "body": body,
                "url": event.source_url,
            }

            try:
                result = classify(notice)
                time.sleep(GROQ_DELAY)
            except Exception as e:
                logger.warning(f"    분류 실패 (스킵): {e}")
                continue

            logger.info(f"    [{result.get('is_snack_event')}] {result.get('reason', '')}")

            if result.get("is_snack_event"):
                try:
                    info = extract_info(notice)
                    time.sleep(GROQ_DELAY)
                except Exception as e:
                    logger.warning(f"    정보 추출 실패: {e}")
                    info = {}

                event.is_snack_event = True
                event.event_date = info.get("date")
                event.event_time = info.get("time")
                event.location = info.get("location")
                event.description = info.get("description") or event.title[:80]
                event.organizer = info.get("organizer")
                event.quantity = info.get("quantity")
                upgraded += 1
                logger.info(f"    ✅ 간식 이벤트로 업그레이드!")

            event.classified_by = CURRENT_MODEL
            db.commit()
            reclassified += 1

        logger.info(f"완료 — 재분류 {reclassified}건, 간식 이벤트로 전환 {upgraded}건")
    finally:
        db.close()


if __name__ == "__main__":
    main()
