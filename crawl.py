#!/usr/bin/env python3
"""크롤러 실행 진입점. GitHub Actions 또는 로컬에서 직접 실행."""

import logging
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from database import Base, SessionLocal, engine
from models import CrawlLog
from classifier.rule_classifier import Classifier
from crawler.runner import run_crawl

logging.basicConfig(level=logging.INFO)

Base.metadata.create_all(bind=engine)

db = SessionLocal()
classifier = Classifier()
log = CrawlLog()
db.add(log)
db.commit()

try:
    result = run_crawl(db, classifier)
    log.finished_at = datetime.utcnow()
    log.total_new = result["total_new"]
    log.snack_events = result["snack_events"]
    log.status = "done"
    print(f"완료 — 신규 {result['total_new']}건, 간식 이벤트 {result['snack_events']}건")
except Exception as e:
    log.finished_at = datetime.utcnow()
    log.status = "error"
    log.error_msg = str(e)
    raise
finally:
    db.commit()
    db.close()
