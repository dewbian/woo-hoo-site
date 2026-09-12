<!-- 파일 목적: woo-hoo.kr 정적 사이트의 SEO+AEO+GEO 3종 최적화 + 구조(인덱스/메뉴) 정비 실행 계획 -->
# PLAN 01 — woo-hoo.kr SEO · AEO · GEO 개편

| | |
|---|---|
| **version** | 0.4 (index 1차 완료 · 커밋 대기) |
| **updated** | 2026-09-12 |
| **status** | 🟢 index 우선 작업 완료(로컬 검증 통과) · 배포(커밋) 승인 대기 / **devlog 관련 전면 보류** |

### ✅ index 1차 완료 (2026-09-12, 로컬 검증)
- P0: index 모바일 햄버거 메뉴 이식 + CTA 메뉴 내 이동 + nav 통일 / watch-notes 404 해소(페이지 신규)
- P1: index head canonical·OG·Twitter Card + Organization·WebSite·ItemList(SoftwareApplication) JSON-LD / hero "Live in stores"→"In store review" 사실 정정
- P2: index FAQ 5문항 + FAQPage JSON-LD / watch-notes AEO Summary
- P3: robots.txt AI봇 명시 Allow / `llms.txt` 생성 / `sameAs`=blog(실존만)
- 산출물 신규: `watch-notes.html`, `llms.txt`, `og-default.png`(1200×630, 브랜드 일치)
- 검증: JSON-LD 2블록 파싱 OK · 내부링크 404 0 · wiring 확인. (라이브 브라우저 렌더는 확장 미연결로 배포 후 확인)
- **미적용(확산 단계)**: about/privacy/apps 랜딩 head·schema, apps `SoftwareApplication`, CWV 실측, BreadcrumbList 전파
| **대상** | 메인 정적 사이트(GitHub Pages): `index/about/devlog/privacy` + `devlog/*`(16개) + **`apps/self-check-study.html`(앱 랜딩)** |
| **제외** | `server/`(블로그 VPS SSR), `blog.woo-hoo.kr`, 루트 `privacy.html` **경로** 변경 |
| **근거 규칙** | `~/.claude/rules/seo-aeo.md` (SEO+AEO+GEO 3종 표준) |

> **불변 원칙 (기존 PLAN 승계)**
> 1. 광고/최적화 작업은 `woo-hoo.kr`(정적)에만. `blog.woo-hoo.kr`(VPS) 무관.
> 2. devlog 본문은 사람이 작성 — Claude는 마크업/구조화까지만.
> 3. 루트 `privacy.html` 경로 변경 금지(스토어 등록 URL).
> 4. 커밋 승인 = main 푸시(배포)까지 한 번에.

---

## 0. 진단 요약 (라이브 실측)

**구조 판정: SPA 아님. 완전 정적 멀티페이지.** JS는 AdSense+구독폼 2개뿐, 콘텐츠는 전부 HTML에 존재 → AI봇이 이미 읽을 수 있음. 병목은 렌더링이 아니라 **구조화 데이터·AEO/GEO 레이어 부재**.

### 🔴 리뷰 발견: 범위 확대 필요 (착수 전 필수)
- **devlog 고아 10개**: `devlog/`에 HTML 16개 존재하나 `devlog.html` 목록·`sitemap.xml`엔 6개만 연결. 나머지 10개(`crawler-robots-block`·`grade-data-normalize`·`kakao-og-image`·`parent-interview`·`play-store-review`·`side-project-infra`·`solo-three-apps`·`tistory-oauth-refresh`·`user-test-once-more`·`cgkSZwL7B9c`[미커밋])는 nav·sitemap 어디에도 없는 고아. **색인/noindex/삭제 결정(D6) 선행** → sitemap·robots·llms.txt 결과가 이에 좌우됨.
- **앱 랜딩 누락**: `apps/self-check-study.html`은 GitHub Pages에 실제 배포되는 앱 홍보 랜딩인데 대상·sitemap에서 빠져 있었음. SEO/GEO 핵심 페이지라 범위에 편입. `ItemList`/`SoftwareApplication` schema도 이 페이지로 연결.
- **hero 통계 상충**: `index.html:774` "01 Live in stores" vs self-check-study "심사중"(`:814,:840`) — JSON-LD로 굳히기 전 사실 정정(심사중이면 SoftwareApplication에 공개 offers/downloadUrl 넣지 않음).

### 현재 상태 매트릭스

| 항목 | index | about | devlog | privacy | devlog/* |
|---|---|---|---|---|---|
| title / description | ✅ | ✅ | ✅ | ✅ | 확인필요 |
| canonical | ❌ | ❌ | ❌ | ❌ | ❌ |
| OG / Twitter Card | ❌ | ❌ | ❌ | ❌ | ❌ |
| JSON-LD 구조화데이터 | ❌ | ❌ | ❌ | ❌ | ❌ |
| Summary 블록(AEO) | ❌ | ❌ | ❌ | — | ❌ |
| 질문형 h2 + 직답 | ❌ | ❌ | ❌ | — | ❌ |
| FAQ + FAQPage | ❌ | ❌ | ❌ | — | ❌ |
| 모바일 햄버거 메뉴 | ❌ | ✅ | ✅ | 해당없음(독립 nav) | 확인필요 |

### 깨진 것 (구조 정비 대상)
- 🔴 `watch-notes.html` **파일 없음** — `index/devlog/about` nav의 `./watch-notes.html` 링크 전부 404.
- 🟠 `index.html` 모바일 메뉴 소실 — `.nav__menu{display:none}`인데 햄버거 버튼 없음(서브페이지엔 있음).
- 🟠 nav 앵커 표기 불일치 — index=`#projects`, 서브=`./#projects`, Watch 링크 제각각.

### 사이트 전역 결손 (GEO/AEO)
- `/llms.txt` 없음 · robots.txt에 AI봇 정책 없음 · `Organization`/`WebSite` 엔티티 schema 없음 · `dateModified` 없음.

---

## 1. 목표 · 성공 기준 (DoD)

1. **SEO**: 전 페이지 canonical·OG·Twitter Card 완비. `Organization`/`WebSite` + 앱목록(`ItemList`+`SoftwareApplication`) + 글(`Article`) + **`BreadcrumbList`(글/리스트/앱 페이지)** JSON-LD 삽입. sitemap 재구성(고아 정리 후).
2. **AEO**: 주요 페이지(index/about/devlog/앱랜딩)에 200자 Summary + 질문형 `<h2>` + FAQ 3개+ & `FAQPage` JSON-LD.
3. **GEO**: `/llms.txt` 생성 · robots.txt AI봇 명시 Allow · `sameAs`로 엔티티 연결(실존 URL만) · 저자/갱신일 표기.
4. **구조**: watch-notes 404 해소 · index 모바일 메뉴 접근 가능 · nav 전 페이지 통일 · devlog 고아 10개 처리(D6).
5. **검증**: 구조화데이터 문법 오류 0 · 내부 링크 404 0 · 모바일 메뉴 동작 · **Core Web Vitals(LCP<2.5s·CLS<0.1·INP<200ms) 실측 통과**.

성공 기준(측정): ① 모든 라우트 `curl` 200/정상, 깨진 내부링크 0 ② JSON-LD 각 블록 유효(schema 검증) ③ CWV 실측치 기준 충족 ④ 규칙 체크리스트(§6 seo-aeo.md) 3종 전부 충족.

---

## 2. 작업 단계 (Phase)

### PHASE 0 — 구조 긴급 픽스 (선행, 독립)
- **0-1 watch-notes 처리**: (A) `watch-notes.html` 신규 생성 or (B) 3개 파일 nav에서 Watch 링크 제거. → **결정 D1**.
- **0-2 index 모바일 메뉴**: 서브페이지의 `.nav__toggle(☰)` + 토글 JS 패턴을 index에 이식. nav 마크업/앵커를 전 페이지 통일.
- **0-3 nav 앵커 정합**: 홈 앵커는 서브페이지에서 `./#...`, index에서 `#...`로 일관 정리.

### PHASE 1 — SEO 뼈대 (전 페이지 head)
- **1-0 devlog 고아 트리아지(선행, D6)**: 16개 각각 색인/noindex/삭제 분류. 색인 대상은 `devlog.html` 목록 + sitemap에 편입, 제외는 `<meta name="robots" content="noindex">` 또는 삭제. `cgkSZwL7B9c.html`(자동생성 추정, 미커밋) 처리 별도 판단.
- **1-1 공통 head 메타**: 각 페이지에 `<link rel="canonical">`(절대 URL), OG(`og:title/description/image/url/type`, og:image=**절대 URL**), Twitter Card(`summary_large_image`) 추가.
- **1-2 엔티티 schema (전역, index head)**: `Organization`(name/url/logo/sameAs — 실존 URL만) + `WebSite` JSON-LD.
- **1-3 앱 schema**: index Projects → `ItemList`, 앱 랜딩(`apps/self-check-study.html`) → `SoftwareApplication`. **심사중 앱은 공개 offers/downloadUrl 미기재**(허위값 금지). hero "01 Live in stores" 사실 정정 동반.
- **1-4 BreadcrumbList**: devlog 글·앱 랜딩·리스트 페이지에 `BreadcrumbList` JSON-LD.
- **1-5 이미지 위생**: 주요 `<img>` alt·width/height·loading 점검·보정.
- **1-6 sitemap/robots**: sitemap 재구성(1-0 결과 반영 + 앱 랜딩·watch-notes 추가) + `lastmod` 갱신.
- **1-7 OG 이미지 제작(D2)**: 전용 1200×630 제작. 정적 사이트라 빌드 없음 → HTML 템플릿을 Chrome/헤드리스로 캡처하거나 디자인 도구로 PNG 생성 후 커밋(기존 feature-graphic 1024×500은 규격 불일치라 재사용 불가).

### PHASE 2 — AEO 레이어 (index/about/devlog)
- **2-1 Summary 블록**: 각 페이지 상단(hero 직후)에 200자 이내 자기완결 요약 문단. 발췌 1순위 타깃.
- **2-2 질문형 h2 + 직답**: 섹션 제목 일부를 자연어 질문형("woo-hoo.kr은 무엇을 만드나요?" 등) + 바로 아래 40~60자 직답(역피라미드). 기존 감성 카피는 시각적 유지하되 접근성 텍스트/구조 보강.
- **2-3 FAQ 섹션**: index(사이트 전반) 3~5개 Q&A + `FAQPage` JSON-LD. (앱/운영/연락 관련 실제 질문 기반)
- **2-4 fact block**: 앱 스펙(플랫폼·가격·상태·출시)을 `<dl>`/카드로 인용가능하게 노출.

### PHASE 3 — GEO 레이어
- **3-1 `/llms.txt`**: 루트에 사이트 개요 + 핵심 페이지 목록/요약(마크다운). (선택 `/llms-full.txt`는 후순위)
- **3-2 robots AI봇 정책**: 현재 `Allow: /`로 이미 전체 허용 상태 → 주요 봇(`ClaudeBot`·`OAI-SearchBot`·`PerplexityBot`·`Google-Extended`)을 **명시적 Allow로 문서화**(정책 가시화, D3=전부 허용).
- **3-3 sameAs·저자·갱신일**: `Organization.sameAs`에 **실존 확인된 URL만** 연결(블로그 blog.woo-hoo.kr 확정 / GitHub·스토어는 실계정 확인 후 — 현재 사이트에 GitHub 링크 없음, 추정 삽입 금지). devlog 글에 `Article.author/datePublished/dateModified`.

### PHASE 4 — 검증 (게이트)
- 4-1 내부 링크 404 스캔(전 페이지 href 크롤).
- 4-2 JSON-LD 문법 검증(각 블록 파싱 + 필수 필드).
- 4-3 모바일 메뉴/반응형 실동작 확인(Chrome).
- 4-4 seo-aeo.md §6 체크리스트 3종 전부 대조.
- 4-5 Core Web Vitals 실측(PageSpeed/Lighthouse) — index 인라인 CSS 58KB+AdSense+폰트3종 부하 확인, 필요시 폰트 subset·preload 조정.
- 4-6 `sec-check.sh`(정적 사이트 해당 항목만) — 헤더는 GitHub Pages 제약상 일부 불가, 적용 가능 범위만.

---

## 3. 결정 사항 (2026-09-12 확정)

| ID | 항목 | 결정 | 후속 영향 |
|---|---|---|---|
| **D1** | ~~watch-notes 링크~~ **취소** | ❌ **오진이었음** | 로컬이 원격보다 41커밋 뒤처져 "404"로 오판. 실제로는 원격에 `watch-notes.html`(자동 "영상노트" 아카이브, gatherThinks 파이프라인, `noindex`)이 이미 존재하며 정상 작동. 신규 제작 불필요 → 내가 만든 페이지 폐기. Watch 메뉴는 자동 페이지 그대로 유지 |
| **D2** | OG 이미지 | ✅ **A) 전용 1200×630 제작** | 사이트 대표 OG 1장 + (선택) 페이지별. HTML→이미지 렌더 방식 |
| **D3** | AI 크롤러 정책 | ✅ **A) 전부 허용** | robots.txt에 주요 AI봇 명시적 `Allow` |
| **D4** | 적용 범위 | ✅ **B) index 먼저→검증→확산** | PHASE 0~3을 index 중심 1차 완성→검증→about/devlog/privacy/devlog* 확산 |
| **D5** | FAQ/카피 내용 | ✅ Claude 초안→사용자 검수 | 감성 카피 유지 + 의미론 텍스트 보강, 허위값 금지 |

**미결(착수 전 결정) — 승인과 함께 확정 필요:**

| ID | 항목 | 옵션 | 권장 |
|---|---|---|---|
| **D6** | devlog 고아 10개 | (A) 전부 색인(목록+sitemap 편입) (B) 일부만 색인·나머지 noindex (C) 불필요분 삭제 | 완성글은 A, 미완/중복/자동생성분은 noindex or 삭제 — 파일별 판단 후 제안 |
| **D1-후속** | watch-notes 콘텐츠 성격 | "요즘 지켜보는 것들"(도구·트렌드·레퍼런스 워치리스트) 등 | 초안 제안 후 검수 |

## 4. 리스크 · 대응
- **GitHub Pages 헤더 한계**: CSP/HSTS 등 응답헤더를 정적 호스팅에서 완전 제어 불가 → 메타·구조 최적화에 집중, 헤더는 적용 가능 범위만(문서에 명시).
- **감성 카피 vs AEO 직답 충돌**: 디자인 훼손 없이 구조 텍스트 보강(시각 카피 유지 + 의미론적 요약 추가). 충돌 시 사용자 확인.
- **JSON-LD 허위 표기 금지**: AggregateRating/가격 등 미확보 값은 넣지 않음(스팸 판정 위험).
- **sameAs URL 정확성**: 실제 존재하는 공식 링크만(GitHub/블로그/스토어) — 추정 금지, 확인 후 삽입.

## 5. 산출물
- 수정: `index/about/devlog/privacy.html`, `apps/self-check-study.html`, `devlog/*.html`, `robots.txt`, `sitemap.xml`
- 신규: `llms.txt`, `watch-notes.html`(D1=A), `og-*.png`(D2=A, 1200×630)
- 결과보고: `docs/result/01_seo-aeo-geo-overhaul.md`

## 6. 다음 액션
1. 본 계획 **독립 리뷰**(별도 세션/서브에이전트, Opus) — 실현성·범위·엣지 검증(글로벌 규칙).
2. D1~D5 결정 확정.
3. PHASE 0부터 순차 착수(D4=B면 index 우선).
