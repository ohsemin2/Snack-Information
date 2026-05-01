"""
크롤링 실행 모듈.
모든 소스를 순회하며 공지사항을 수집하고, 미분류 글을 DB에 저장한 뒤
Groq 분류기로 간식 이벤트 여부를 판별한다.

증분 크롤링: 소스별로 마지막으로 본 URL을 북마크로 저장.
첫 실행은 1페이지만 수집해 기준점을 세우고, 이후엔 북마크 URL까지만 수집.
"""

import time
import logging
from datetime import date, timedelta, datetime

from config import SOURCES, REQUEST_DELAY, MAX_PAGES_PER_SOURCE, GROQ_DELAY
from crawler.sources import get_parser, fetch_body
from crawler.dedup import url_hash
from classifier.rule_classifier import CURRENT_MODEL

logger = logging.getLogger(__name__)


def _cleanup_old_events(db_session):
    from models import Event
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    deleted = db_session.query(Event).filter(
        Event.is_snack_event == True,
        Event.event_date.isnot(None),
        Event.event_date < cutoff,
    ).delete(synchronize_session=False)
    db_session.commit()
    if deleted:
        logger.info(f"[CLEANUP] {deleted}건 삭제 (event_date 30일 초과)")


def run_crawl(db_session, classifier):
    from models import CrawlLog, Event, SourceBookmark

    _cleanup_old_events(db_session)

    total_new = 0
    total_snack = 0

    for source in SOURCES:
        parser = get_parser(source)
        logger.info(f"[CRAWL] {source['name']} 시작")

        bookmark = db_session.query(SourceBookmark).filter_by(source_name=source['name']).first()
        bookmark_url = bookmark.latest_url if bookmark else None
        is_first_run = bookmark is None
        max_pages = 1 if is_first_run else MAX_PAGES_PER_SOURCE
        newest_url = None

        for page in range(1, max_pages + 1):
            notices = parser.get_notices(page=page)
            if not notices:
                break

            hit_bookmark = False
            for notice in notices:
                url = notice.get("url", "")
                if not url:
                    continue

                if newest_url is None:
                    newest_url = url

                if bookmark_url and url == bookmark_url:
                    hit_bookmark = True
                    break

                key = url_hash(url)
                existing = db_session.query(Event).filter_by(url_hash=key).first()
                if existing:
                    if existing.is_snack_event or existing.classified_by == CURRENT_MODEL:
                        continue
                    db_session.delete(existing)
                    db_session.commit()

                time.sleep(REQUEST_DELAY)
                body = fetch_body(url)
                notice["body"] = body

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
                        classified_by=CURRENT_MODEL,
                    )
                    db_session.add(event)
                    db_session.commit()
                    total_snack += 1
                    logger.info(f"  ✅ 간식 이벤트 저장: {notice['title']}")
                else:
                    non_event = Event(
                        url_hash=key,
                        source_name=notice["source_name"],
                        title=notice["title"],
                        source_url=url,
                        raw_date=notice.get("date", ""),
                        is_snack_event=False,
                        classified_by=CURRENT_MODEL,
                    )
                    db_session.add(non_event)
                    db_session.commit()

                total_new += 1

            if hit_bookmark:
                break

            time.sleep(REQUEST_DELAY)

        if newest_url:
            if bookmark:
                bookmark.latest_url = newest_url
                bookmark.updated_at = datetime.utcnow()
            else:
                db_session.add(SourceBookmark(source_name=source['name'], latest_url=newest_url))
            db_session.commit()

        logger.info(f"[CRAWL] {source['name']} 완료")

    logger.info(f"[CRAWL] 전체 완료 — 신규 {total_new}건, 간식 이벤트 {total_snack}건")
    return {"total_new": total_new, "snack_events": total_snack}
