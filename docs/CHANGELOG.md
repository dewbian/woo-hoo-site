<!-- 파일 목적: woo-hoo.kr 애드센스 작업 실행 결과 누적 기록 -->
# CHANGELOG — woo-hoo.kr 애드센스 작업

## 2026-06-07 · 블로그(server/) 단일 카테고리 하드 필터

### 배경
- `blog.woo-hoo.kr` 자체의 애드센스 거절 사유 = **같은 원문을 여러 페르소나로 중복 발행**(scaled/duplicate content). → 카테고리(angle) **하나만** 노출하도록 변경.

### 완료
- `BlogRepo` 에 `only_angle` 단일 카테고리 하드 필터 추가 — 목록·무한스크롤(cards)·상세·sitemap·feed **전 영역** 적용. 타 카테고리 상세 URL 직접 접근도 404 처리. 필터 칩은 자동 숨김(`angles()` → `[]`).
- `main.py`: `BLOG_ONLY_ANGLE` 환경변수(기본 `주식소식`)로 제어. 빈 값이면 전체 노출로 복귀.
- **라이브 Supabase 검증**: `articles.angle` 실측 결과 `주식소식` 발행 64건 존재 확인 → 추측(`경제 애널리스트`) 대신 실제 값 `주식소식` 으로 확정. E2E 확인(목록 64건 전부 주식소식 / 타 카테고리 상세 None / 칩 숨김).
- `list.html` 히어로 카피 단일 관점으로 수정("여섯 사람의 눈으로" 제거).
- `.env` / `.env.example` 에 `BLOG_ONLY_ANGLE=주식소식` 명시.

### 변경 파일
`server/blog.py`, `server/main.py`, `server/templates/list.html`, `server/.env`, `server/.env.example`

### 확인 사항
- 기존 테스트 34개 전부 통과(순수함수·라우트). 배포는 사용자가 VPS(:8001)에서 진행.
- 카테고리를 바꾸려면 `.env` 의 `BLOG_ONLY_ANGLE` 만 수정 후 재기동.

---

## 2026-06-07 · v0.3 — PHASE 2 devlog 구조화 완료

### 완료
- **개별 글 페이지 신설**: 정적 `/devlog/{slug}.html` 3편 — `stamp-interaction`(self-check-study), `persona-pipeline`(make-money), `stability-score`(googSky).
- **공유 스타일**: `devlog/_post.css` (히어로·본문·이전다음·다른개발기 레이아웃, styles.css 토큰 재사용).
- **글 구조**: 제목/작성일/태그칩/본문 + 관련 프로젝트 콜아웃(`#projects`) + 이전·다음 글 네비 + "다른 개발기 보기" 목록. 본문은 기존 메모를 이식하고 1,000자+ 확장 가이드를 HTML 주석으로 삽입(가짜 분량 미작성).
- **인덱스 연결**: `devlog.html` 타임라인을 개별 글로 연결되는 목록으로 전환, `index.html` `#devlog` 미리보기 3개 제목에 링크 부여.
- **SEO**: `sitemap.xml` 에 개별 글 3건 추가.

### 변경 파일
`devlog/_post.css`(신규), `devlog/stamp-interaction.html`(신규), `devlog/persona-pipeline.html`(신규), `devlog/stability-score.html`(신규), `devlog.html`, `index.html`, `sitemap.xml`, `docs/PLAN.md`

### 다음 할 일
- PHASE 3: 개별 글 본문 1,000자+ 확장(사용자) + 추가 글 스캐폴딩으로 12~15편 확보.

---

## 2026-06-07 · v0.2 — PHASE 1 신뢰성/구조 정비 완료

### 완료
- **깨진 링크 일소**: index/devlog의 빈 `href="#"` 전부 제거 또는 실링크 연결. nav 브랜드→`/`.
- **앱 Privacy 404 해소 (★최우선 리스크)**: 루트 `privacy/` 폴더 부재로 404였던 카드 3개 + 푸터 2곳을 모두 루트 `./privacy.html` 로 통합.
- **About 페이지 신설**: `about.html` (운영자·운영철학·앱 라인업·연락처). index/devlog nav·푸터에서 연결.
- **이메일 통일**: 전 페이지 `woohoo.dew1017@gmail.com` 로 일원화 (devlog의 `dev@b-lot.co.kr` 교체).
- **Privacy 광고 문구**: `privacy.html` 에 "광고 및 쿠키(Google AdSense)" + "제3자 사이트 링크 면책" 섹션 추가 (쿠키·DoubleClick·adssettings·aboutads 고지).
- **블로그 격리**: `blog.woo-hoo.kr` 링크 3곳(nav/티커/푸터) `rel="nofollow"` (승인 후 원복 예정).
- **SEO/크롤러**: `sitemap.xml` 신규 생성, `robots.txt` 에 Sitemap 라인 추가.
- **devlog nav 정정**: 존재하지 않던 앵커 `#products`/`#download` → `#projects`/About 로 교체.

### 변경 파일
`index.html`, `devlog.html`, `about.html`(신규), `privacy.html`, `sitemap.xml`(신규), `robots.txt`, `docs/PLAN.md`

### 결정 확정 (D1~D5)
이메일 통일 / Play 버튼 "출시 예정" 비활성 / GitHub·X 삭제 / Privacy 루트 통합 / 정적 `/devlog/slug.html`

### 다음 할 일
- PHASE 2: `/devlog/{slug}.html` 개별 페이지 템플릿 + 인덱스 연결, 기존 메모 3편 우선 페이지화.
- PHASE 3: 완성글 12~15편 스캐폴딩 (본문은 사용자 작성).
- (선택) `terms.html` 추가 검토.
