# snackInfo — CLAUDE.md

## 프로젝트 개요

서울대학교 각 단과대/기관 공지사항을 자동 크롤링하여 **무료 간식 나눔 행사**만 추출·정리해 보여주는 웹 서비스.

- 크롤러가 공지사항을 수집하면 Claude API(Haiku)가 간식 이벤트 여부를 판별하고 구조화된 정보(날짜·시간·장소·주최·수량)를 추출
- FastAPI 백엔드가 SQLite에 저장하고 REST API로 제공
- 바닐라 JS 프론트엔드(단일 HTML 파일)가 이를 카드 형식으로 표시

## 디렉터리 구조

```
snackInfo/
├── config.py              # 크롤링 소스 목록, 간격, 딜레이 등 전역 설정
├── run.sh                 # 백엔드 실행 스크립트 (uvicorn)
├── requirements.txt       # Python 의존성
├── .env.example           # 환경변수 샘플 (ANTHROPIC_API_KEY)
│
├── backend/
│   ├── main.py            # FastAPI 앱, 스케줄러, API 엔드포인트
│   ├── models.py          # SQLAlchemy 모델 (Event, CrawlLog)
│   └── database.py        # SQLite 엔진 및 세션 설정
│
├── crawler/
│   ├── runner.py          # 크롤링 + 분류 파이프라인 (run_crawl)
│   ├── sources.py         # 사이트별 파서 클래스 + fetch_body
│   └── dedup.py           # URL SHA-256 해싱으로 중복 방지
│
├── classifier/
│   └── claude_client.py   # Claude API 래퍼 (classify, extract_info)
│
└── frontend/
    └── index.html         # 단일 파일 프론트엔드 (바닐라 JS)
```

## 핵심 데이터 흐름

```
SOURCES (config.py)
  → crawler/runner.py::run_crawl()
      → 각 파서의 get_notices(page)      # 목록 수집
      → crawler/sources.py::fetch_body() # 상세 본문 수집
      → classifier.classify()            # 간식 이벤트 판별
      → classifier.extract_info()        # 구조화 정보 추출
      → DB에 Event 저장
  → FastAPI /events, /events/today       # 프론트엔드에 제공
```

## 주요 설정값 (config.py)

| 변수 | 기본값 | 설명 |
|---|---|---|
| `CRAWL_INTERVAL_SECONDS` | 3600 | 자동 크롤링 주기 (초) |
| `REQUEST_DELAY` | 1.5 | 요청 사이 딜레이 (서버 부하 방지) |
| `MAX_PAGES_PER_SOURCE` | 3 | 소스당 최대 페이지 수 |

## 파서 타입

`config.py`의 각 소스는 `type` 필드로 파서를 지정한다.

| type | 파서 클래스 | 대상 사이트 |
|---|---|---|
| `standard` | `StandardParser` | 대부분의 단과대 (SNU 표준 CMS) |
| `snu_main` | `SnuMainParser` | 서울대 본부 (www.snu.ac.kr) |
| `snu_cms` | `SnuCmsParser` | JSP 기반 CMS (eng.snu.ac.kr 등) |
| `wordpress` | `WordPressParser` | WordPress 기반 (음대, 건축학과, 학부대학) |
| `gnuboard` | `GnuBoardParser` | 그누보드 (convergence.snu.ac.kr) |

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/events` | 오늘 이후 간식 이벤트 목록 (날짜 미정 포함) |
| GET | `/events/today` | 오늘 행사만 |
| GET | `/events/{id}` | 이벤트 상세 (raw_body 포함) |
| POST | `/crawl/trigger` | 수동 크롤링 즉시 실행 |
| GET | `/crawl/status` | 최근 크롤링 로그 5건 |

## DB 모델

**Event**: `url_hash`(고유키), `source_name`, `source_url`, `title`, `raw_date`, `raw_body`, `is_snack_event`, `event_date`(YYYY-MM-DD), `event_time`, `location`, `description`, `organizer`, `quantity`

**CrawlLog**: `started_at`, `finished_at`, `total_new`, `snack_events`, `status`(running/done/error), `error_msg`

## Claude API 사용 방식

- 모델: `claude-haiku-4-5-20251001` (비용 효율)
- `classify()`: 본문 앞 600자만 사용, `is_snack_event` + `reason` 반환
- `extract_info()`: 본문 앞 2000자 사용, 날짜/시간/장소/설명/주최/수량 추출
- 응답은 항상 JSON. 코드블록(```)이 있으면 파싱 전 제거

## 환경 설정

```bash
cp .env.example .env
# .env에 ANTHROPIC_API_KEY 설정 후:
./run.sh
```

프론트엔드는 `frontend/index.html`을 브라우저에서 직접 열거나 `http://localhost:8000` 접속.

## 새 소스 추가 방법

`config.py`의 `SOURCES` 리스트에 항목 추가:

```python
{
    "name": "단과대/기관명",
    "url": "공지사항 목록 URL",
    "type": "standard",  # 위 파서 타입 참고
}
```

기존 파서로 파싱이 안 되는 사이트는 `crawler/sources.py`에 새 파서 클래스를 추가하고 `get_parser()` 팩토리에 등록한다.

## 주의사항

- `is_snack_event=False`인 공지사항도 DB에 저장됨 — 재크롤링 시 중복 처리 방지용
- 간식 이벤트 판별 기준: 제목/본문에 "간식" 키워드가 없으면 false, 채용공고·세미나 부수 다과도 false
- `event_date`가 null인 이벤트도 `/events`에 포함됨 (날짜 미정)
