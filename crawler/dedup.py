"""URL 기반 중복 제거 유틸리티."""

import hashlib


def url_hash(url: str) -> str:
    """URL을 SHA-256으로 해싱해 고유 키를 반환한다."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()
