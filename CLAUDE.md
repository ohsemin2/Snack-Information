# snackInfo — CLAUDE.md

## 프로젝트 개요

서울대학교 각 단과대/기관 공지사항을 자동 크롤링하여 **무료 간식 나눔 행사**만 추출·정리해 보여주는 웹 서비스.

- GitHub Actions 크론으로 `crawl.py`를 주기 실행
- Groq API(llama-3.1-8b-instant)가 간식 이벤트 여부를 판별하고 구조화된 정보(날짜·시간·장소·주최·수량)를 추출
- 결과를 Supabase(PostgreSQL)에 저장
- 바닐라 JS 프론트엔드(단일 HTML 파일)가 Supabase REST API를 직접 호출해 카드 형식으로 표시

## 디렉터리 구조

```
snackInfo/
├── config.py              # 크롤링 소스 목록, 딜레이, 최대 페이지 수 등 전역 설정
├── crawl.py               # 크롤러 실행 진입점 (GitHub Actions에서 호출)
├── models.py              # SQLAlchemy 모델 (Event, CrawlLog)
├── database.py            # Supabase(PostgreSQL) 엔진 및 세션 설정
├── requirements.txt       # Python 의존성
│
├── .github/
│   └── workflows/
│       └── crawl.yml      # GitHub Actions 크론 스케줄
│
├── crawler/
│   ├── runner.py          # 크롤링 + 분류 파이프라인 (run_crawl)
│   ├── sources.py         # 사이트별 파서 클래스 + fetch_body
│   └── dedup.py           # URL SHA-256 해싱으로 중복 방지
│
├── classifier/
│   └── rule_classifier.py # Groq API 래퍼 (classify, extract_info)
│
└── frontend/
    └── index.html         # 단일 파일 프론트엔드 (바닐라 JS, Supabase 직접 호출)
```

## 핵심 데이터 흐름

```
GitHub Actions cron
  → crawl.py
      → run_crawl(db, classifier)
          → 각 파서의 get_notices(page)      # 목록 수집
          → crawler/sources.py::fetch_body() # 상세 본문 수집
          → classifier.classify()            # 간식 이벤트 판별 (Groq)
          → classifier.extract_info()        # 구조화 정보 추출 (Groq)
          → Supabase events 테이블에 저장

frontend/index.html
  → Supabase REST API 직접 호출 → 카드 렌더링
```

## 주요 설정값 (config.py)

| 변수 | 기본값 | 설명 |
|---|---|---|
| `REQUEST_DELAY` | 1.5 | 요청 사이 딜레이 (서버 부하 방지) |
| `MAX_PAGES_PER_SOURCE` | 5 | 소스당 최대 페이지 수 |

> `CRAWL_INTERVAL_SECONDS`는 config.py에 정의되어 있으나 실제 스케줄은 `.github/workflows/crawl.yml` cron으로 제어된다.

## 파서 타입

`config.py`의 각 소스는 `type` 필드로 파서를 지정한다.

| type | 파서 클래스 | 대상 사이트 |
|---|---|---|
| `standard` | `StandardParser` | 대부분의 단과대 (SNU 표준 CMS) |
| `snu_main` | `SnuMainParser` | 서울대 본부 (www.snu.ac.kr) |
| `snu_cms` | `SnuCmsParser` | JSP 기반 CMS (eng.snu.ac.kr 등) |
| `wordpress` | `WordPressParser` | WordPress 기반 (음대, 건축학과, 학부대학 등) |
| `gnuboard` | `GnuBoardParser` | 그누보드 (convergence.snu.ac.kr) |

`StandardParser`는 `custom_selector` 옵션으로 CSS 선택자를 직접 지정할 수 있다.

## DB 모델

**Event**: `url_hash`(고유키), `source_name`, `source_url`, `title`, `raw_date`, `raw_body`, `is_snack_event`, `event_date`(YYYY-MM-DD), `event_time`, `location`, `description`, `organizer`, `quantity`

**CrawlLog**: `started_at`, `finished_at`, `total_new`, `snack_events`, `status`(running/done/error), `error_msg`

## Groq API 사용 방식

- 모델: `llama-3.1-8b-instant`
- `classify()`: 본문 앞 600자만 사용, `is_snack_event` + `reason` 반환
- `extract_info()`: 본문 앞 2000자 사용, 날짜/시간/장소/설명/주최/수량 추출
- 응답은 JSON 오브젝트 형식으로 강제 (`response_format={"type": "json_object"}`)

## 환경변수

| 변수 | 설명 |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL 연결 문자열 |
| `GROQ_API_KEY` | Groq API 키 |

GitHub Actions Secrets에 등록해야 한다. 로컬 실행 시 `.env` 파일로 설정.

## GitHub Actions 스케줄

`.github/workflows/crawl.yml`에서 cron으로 실행 주기를 제어한다. `workflow_dispatch`로 수동 실행도 가능.

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
- 간식 이벤트 판별 기준: 학생에게 무료로 음식/간식을 나눠주는 행사만 true. 채용공고, 세미나 부수 다과, 식당 메뉴 안내는 false
- `event_date`가 null인 이벤트도 프론트엔드에 표시됨 (날짜 미정)
- `requests.get`에 `verify=False` 적용 중 (일부 SNU 사이트 SSL 인증서 문제 우회)
