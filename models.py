from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text

from database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    url_hash = Column(String(64), unique=True, index=True, nullable=False)

    source_name = Column(String(100))
    source_url = Column(String(500))

    title = Column(String(300))
    raw_date = Column(String(50))
    raw_body = Column(Text)

    is_snack_event = Column(Boolean, default=True)
    event_date = Column(String(10))
    event_time = Column(String(50))
    location = Column(String(200))
    description = Column(String(300))
    organizer = Column(String(100))
    quantity = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    total_new = Column(Integer, default=0)
    snack_events = Column(Integer, default=0)
    status = Column(String(20), default="running")
    error_msg = Column(Text)
