# woo-hoo.kr 블로그 "세상만사 구경만사" 설계 — 뉴스 글 동적 게시

- **작성일:** 2026-05-28
- **대상:** `woo-hoo.kr` (기존 GitHub Pages 정적 + 신규 `/blog` 파이썬 동적 서버)
- **목표:** make-money가 Supabase에 쌓는 LLM 가공 뉴스 글을, woo-hoo.kr `/blog`("세상만사 구경만사")에 동적(SSR)으로 게시하고 Google AdSense로 수익화한다.
- **상태:** 설계 승인됨 — 구현 계획(writing-plans) 대기

---

## 1. 배경 & 목적

`make-money`는 로컬에서 돌리는 Python 자동화 도구로, 뉴스를 크롤링 → 키워드 추출 → 페르소나(angle)별 LLM 글 생성 → 티스토리/네이버 발행까지 한다. 생성된 글은 Supabase `articles` 테이블에 쌓인다.

이 글들을 woo-hoo.kr 자체 블로그("세상만사 구경만사")에도 게시해서:
- **살아 움직이는 사이트** — 뉴스 글이 계속 쌓여 사이트가 자란다 (woo-hoo.kr 브랜드 컨셉과 부합).
- **애드센스 수익** — 블로그 글에 광고 게재.

### 핵심 제약 (반드시 지킬 것)
- **make-money 코드는 건드리지 않는다.** Supabase를 읽기 전용 데이터 소스로만 공유한다.
- **루트 `privacy.html` URL과 CNAME은 절대 변경 금지.** self-check-study의 Google Play 심사 등록 URL이라 404 시 앱이 위험. → 그래서 블로그는 기존 GitHub Pages를 건드리지 않는 리버스 프록시 방식(②)으로 분리한다.

---

## 2. 확정 아키텍처 — 리버스 프록시 + 동적 SSR

```
[make-money] (안 건드림) ──→ [Supabase] articles  ←─ 읽기 전용 데이터 소스
                                    │ (서버사이드 읽기)
[GitHub: woo-hoo-site 레포] ← 소스 관리              │
  · 정적: /index /privacy.html /apps  (GitHub Pages) │
  · server/  파이썬 FastAPI 코드                      │
  · .github/workflows/deploy.yml                      │
        │ push                                        │
        ▼                                             │
[GitHub Actions] ─SSH 배포 + 서비스 재시작→ [준비한 웹서버]┘
                                            Gunicorn+Uvicorn
                                            FastAPI SSR (localhost:8000)
                                            Nginx(443) → 8000

        ┌──────── woo-hoo.kr 라우팅 (Cloudflare 앞단) ────────┐
        │  /blog/*  → 파이썬 서버 (동적 SSR → SEO ✅)         │
        │  나머지   → GitHub Pages (privacy.html 그대로, 0 리스크) │
        └─────────────────────────────────────────────────────┘
```

### 결정 근거 요약
- **왜 동적 SSR인가:** 사용자가 "Python이 DB 붙어 렌더"하는 구조를 선호. SSR이라 봇이 완성 HTML을 받아 **SEO·공유 카드 정상**.
- **왜 리버스 프록시(②)인가:** `privacy.html`·CNAME을 0 리스크로 보존하면서 동적 블로그를 같은 woo-hoo.kr 도메인 경로(`/blog`)에 붙일 수 있음. 서브도메인 분리 안 함.
- **왜 make-money 미수정인가:** make-money의 claim/dispatcher 발행 로직에 엮이지 않고 관심사 분리. 블로그는 woo-hoo-site 레포에서 self-contained.

---

## 3. 데이터 모델 — Supabase `articles` 읽기

### 3.1 기존 스키마 (make-money 소유, 읽기만)
```
news (크롤링 원본) → keywords (추출 키워드) → articles (LLM 글) → publications (발행 기록)
```
- `articles`: `id, keyword_id, angle, content(마크다운), char_count, status, created_at, claimed_by, ...`
- 본문 = `articles.content` (마크다운)
- 관점/페르소나 = `articles.angle` (경제 애널리스트·데이터 정리광·따뜻한 에세이스트·회의적 분석가·Z세대·학부모 등)
- 원본 뉴스 = `articles → keywords.news_id → news.title/url` 조인

### 3.2 글 선택 기준
- **`status = '완료'` 인 article 전부** 를 블로그에 노출 (최신순).
- woo-hoo 전용 플래그는 두지 않음 (make-money/DB 미변경). → woo-hoo.kr이 사실상 메인 발행처.
- ⚠️ **중복 콘텐츠 주의:** 같은 글을 티스토리에도 발행하면 검색 중복이 생김. woo-hoo.kr 검색 노출을 우선하려면 그 글을 티스토리에 중복 발행하지 않는 운영이 필요. (canonical = self)

### 3.3 블로그 필드 파생 규칙 (articles엔 title/slug/summary/썸네일이 없음)

| 블로그 필드 | 파생 규칙 |
|---|---|
| 제목 | `content` 첫 `# H1`(없으면 `## H2`, 없으면 첫 줄 100자). make-money `tistory._extract_title` 로직과 동일하게 구현 |
| 본문 | `content`에서 첫 H1 줄 제거 후 markdown-it-py로 HTML 변환 |
| 요약 | 본문 plain text 앞 ~120자 (목록 카드 + `og:description`) |
| URL/식별 | `/blog/<article_id>` (한글 제목이라 id 기반. SEO 키워드는 `<title>`·`<h1>`·OG로 충족) |
| 페르소나 | `angle` 그대로 표시 + 목록 필터 |
| 썸네일 | angle(페르소나)별 대표 그래픽 (v2 보라 톤, 6종 색/아이콘) — `og:image`·목록 카드용 |
| 발행일 | `created_at` 최신순 |

---

## 4. URL & 라우팅 (FastAPI)

| 경로 | 설명 | 렌더 |
|---|---|---|
| `GET /blog` | 목록 ("세상만사 구경만사"). 페이지네이션·페르소나 필터 | `list.html` SSR |
| `GET /blog/<id>` | 글 상세. 마크다운→HTML + 애드센스 | `detail.html` SSR |
| `GET /blog/sitemap.xml` | 발행 글 sitemap (SEO) | 동적 생성 |
| `GET /blog/feed.xml` | RSS (선택) | 동적 생성 |

- 잘못된/미존재 id, status≠완료 → **404**.
- 빈 목록 → "아직 글이 없어요" 빈 상태 UI.

---

## 5. 블로그 UI

- **디자인 톤:** woo-hoo.kr v2 디자인 시스템 계승 (보라 `#7C3AED` / 라벤더 크림 / 잉크 / Instrument Serif 디스플레이 / Pretendard 본문 / JetBrains Mono). 토큰은 템플릿/CSS에 인라인 사본.
- **타이틀:** "세상만사 구경만사".
- **목록(`list.html`):** 헤더(타이틀) + 페르소나 필터 칩 + 글 카드 그리드(썸네일·제목·요약·페르소나 배지·날짜) + 페이지네이션.
- **상세(`detail.html`):** 제목(h1) + 페르소나 배지 + 발행일 + 본문(article) + 애드센스 슬롯 + (선택)원본 뉴스 출처 링크.
- 기존 woo-hoo.kr 헤더/푸터와 시각적으로 연결되게 (한 사이트 느낌).

---

## 6. Google AdSense

- 상세 템플릿(`detail.html`)에 AdSense JS 삽입. 위치: 본문 시작 직후 + 본문 끝(인아티클 유닛 2개) 또는 자동 광고 스크립트.
- publisher ID(`ca-pub-...`)는 **미정 (TODO)** — 구현 시 설정값으로 주입 (환경변수).
- ⚠️ **정책 리스크 (기록):** Google AdSense는 자동 생성/저가치 콘텐츠에 승인 거부·게재 제한·정지를 둘 수 있음. 자동 뉴스 글이 정책에 걸릴 가능성을 인지하고 진행. (설계 결정 아님, 운영 리스크 고지)

---

## 7. 인프라 & 배포

### 7.1 파이썬 서버 스택 (make-money와 동일 생태계)
| 역할 | 라이브러리 |
|---|---|
| 웹 | FastAPI |
| 실행 | Uvicorn(개발) / Gunicorn+UvicornWorker(운영), systemd 상시 |
| 템플릿 | Jinja2 |
| 마크다운→HTML | markdown-it-py |
| Supabase | supabase-py (읽기 전용 키) |

### 7.2 코드 구조 (woo-hoo-site 레포)
```
woo-hoo-site/
├── index.html · privacy.html · apps/   ← 기존 정적 (GitHub Pages, 불변)
└── server/                              ← 신규 FastAPI
    ├── main.py            (FastAPI 앱·라우트)
    ├── blog.py            (Supabase 읽기 + 제목/요약 파생)
    ├── templates/         (list.html, detail.html)
    ├── static/            (블로그 CSS, v2 토큰)
    ├── requirements.txt
    └── .env.example       (SUPABASE_URL, SUPABASE_KEY, ADSENSE_PUB_ID)
```

### 7.3 리버스 프록시 (Cloudflare)
- woo-hoo.kr DNS를 Cloudflare로 관리.
- Origin Rule: `woo-hoo.kr/blog/*` → 준비한 웹서버 origin. 나머지 → GitHub Pages origin.
- **전환 안전 절차:** Cloudflare 적용 후 `/`, `/privacy.html`, `/apps/`가 여전히 정상 응답하는지 확인한 뒤 `/blog` 라우팅 추가. privacy.html은 GitHub Pages가 계속 서빙.

### 7.4 배포 (GitHub Actions)
- `push` → Actions가 준비한 웹서버에 SSH 접속 → 코드 동기화(git pull 또는 rsync) → 의존성 설치 → systemd 서비스 재시작.
- secrets: 서버 SSH 키, `SUPABASE_URL`, `SUPABASE_KEY`, `ADSENSE_PUB_ID`.
- 순수 SFTP는 정적 파일엔 충분하나 동적 서버는 재시작이 필요해 SSH 단계를 포함.

---

## 8. 에러 처리 & 엣지 케이스

- **Supabase 연결 실패:** 503 에러 페이지 (간단). 선택적으로 짧은 TTL 인메모리 캐시로 완화.
- **성능/부하:** 매 요청 DB 조회 → 목록·상세에 짧은 TTL(예 60초) 캐시 또는 Cloudflare 캐시로 완화.
- **제목 없는 본문:** H1/H2 없으면 첫 비어있지 않은 줄 100자, 그래도 없으면 "제목 없음".
- **마크다운 안전:** LLM 생성 본문 렌더 시 XSS 방지 (markdown-it 설정에서 raw HTML 비허용 또는 sanitize).
- **404:** 미존재/미완료 id.
- **SEO 태그:** 각 상세에 `<title>`, `meta description`, OG(title/description/image/url), `canonical`(self). sitemap.xml 제공.

---

## 9. 테스트 전략

- **단위:** 제목/요약 파생 함수(다양한 마크다운 입력), slug/URL 생성, 마크다운→HTML 변환·sanitize.
- **통합:** Supabase 읽기(테스트 데이터 또는 모킹) → 목록/상세 렌더, 404 경로, 빈 목록.
- **수동 QA:** 실제 글로 목록·상세 렌더 확인, 카톡 공유 카드(OG) 확인, 애드센스 슬롯 표시, 모바일 반응형.

---

## 10. 미결 항목 (구현 전 채울 것)

1. **AdSense publisher ID** (`ca-pub-...`) — 환경변수로 주입.
2. **준비한 웹서버 정보** — 종류/접속(SSH)/공개 도메인 또는 IP, 포트.
3. **Cloudflare 사용 여부 / DNS 관리 위치** — 리버스 프록시 설정 주체.

---

## 11. 스코프 밖 (Non-goals)

- make-money 코드 수정, 발행 플랫폼("woohoo") 추가 — 하지 않음.
- 글 작성/편집 관리자 UI — 글 생산은 make-money 담당.
- 댓글, 검색 엔진(자체), 회원 기능 — 초기 범위 아님.
- 정적 생성(SSG)·GitHub Pages 동적화 — 채택 안 함(동적 SSR로 결정).
