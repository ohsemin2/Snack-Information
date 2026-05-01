"""
크롤링 실행 모듈.
모든 소스를 순회하며 공지사항을 수집하고, 미분류 글을 DB에 저장한 뒤
Claude 분류기로 간식 이벤트 여부를 판별한다.
"""

import time
import logging

from config import SOURCES, REQUEST_DELAY, MAX_PAGES_PER_SOURCE, GROQ_DELAY
from crawler.sources import get_parser, fetch_body
from crawler.dedup import url_hash

logger = logging.getLogger(__name__)


def run_crawl(db_session, classifier):
    """
    전체 크롤링 + 분류 파이프라인.

    Args:
        db_session: SQLAlchemy 세션
        classifier: classifier.claude_client.Classifier 인스턴스
    """
    from models import CrawlLog, Event

    total_new = 0
    total_snack = 0

    for source in SOURCES:
        parser = get_parser(source)
        logger.info(f"[CRAWL] {source['name']} 시작")

        for page in range(1, MAX_PAGES_PER_SOURCE + 1):
            notices = parser.get_notices(page=page)
            if not notices:
                break

            new_in_page = 0
            for notice in notices:
                url = notice.get("url", "")
                if not url:
                    continue

                key = url_hash(url)

                # 이미 처리한 URL이면 스킵
                existing = db_session.query(Event).filter_by(url_hash=key).first()
                if existing:
                    continue

                # 상세 페이지에서 본문 가져오기
                time.sleep(REQUEST_DELAY)
                body = fetch_body(url)
                notice["body"] = body

                # Groq로 분류 — API 오류 시 저장하지 않고 스킵 (다음 크롤링에서 재시도)
                try:
                    result = classifier.classify(notice)
                    time.sleep(GROQ_DELAY)
                except Exception as e:
                    logger.warning(f"  ⚠️ 분류 실패 (스킵): {notice['title']} — {e}")
                    continue

                logger.info(f"  [{result.get('is_snack_event')}] {notice['title']} — {result.get('reason', '')}")
                if result.get("is_snack_event"):
                    try:
                        info = classifier.extract_info(notice)
                        time.sleep(GROQ_DELAY)
                    except Exception as e:
                        logger.warning(f"  ⚠️ 정보 추출 실패 (기본값 사용): {e}")
                        info = {"date": None, "time": None, "location": None,
                                "description": notice["title"][:80], "organizer": None, "quantity": None}
                    event = Event(
                        url_hash=key,
                        source_name=notice["source_name"],
                        title=notice["title"],
                        source_url=url,
                        raw_date=notice.get("date", ""),
                        event_date=info.get("date"),
                        event_time=info.get("time"),
                        location=info.get("location"),
                        description=info.get("description"),
                        organizer=info.get("organizer"),
                        quantity=info.get("quantity"),
                        raw_body=body[:5000],
                    )
                    db_session.add(event)
                    db_session.commit()
                    total_snack += 1
                    logger.info(f"  ✅ 간식 이벤트 저장: {notice['title']}")
                else:
                    # 간식 이벤트 아님 — URL만 기록해 다음 크롤링에서 재처리 방지
                    non_event = Event(
                        url_hash=key,
                        source_name=notice["source_name"],
                        title=notice["title"],
                        source_url=url,
                        raw_date=notice.get("date", ""),
                        is_snack_event=False,
                    )
                    db_session.add(non_event)
                    db_session.commit()

                new_in_page += 1
                total_new += 1

            # 페이지에서 새 글이 없으면 더 이상 순회할 필요 없음
            if new_in_page == 0:
                break

            time.sleep(REQUEST_DELAY)

        logger.info(f"[CRAWL] {source['name']} 완료")

    logger.info(f"[CRAWL] 전체 완료 — 신규 {total_new}건, 간식 이벤트 {total_snack}건")
    return {"total_new": total_new, "snack_events": total_snack}
