<!-- 파일 목적: woo-hoo.kr 애드센스 재심사 통과를 위한 실행 계획 (라이브 실측 기반) -->
# PLAN — woo-hoo.kr 애드센스 통과 작업

| | |
|---|---|
| **version** | 0.4 |
| **updated** | 2026-06-08 |
| **status** | 🟢 PHASE 1·2 + PHASE 3 스캐폴딩 완료 / 본문 작성 대기 |
| **근거 문서** | `docs/ADSENSE_TASK.md` (전략 A안) |
| **거절 사유** | thin content — 고유 콘텐츠 + 신뢰성 페이지 부족 |

> **불변 원칙**
> 1. 광고 코드는 `woo-hoo.kr` 에만. `blog.woo-hoo.kr`(자동 뉴스)엔 절대 금지.
> 2. devlog 본문은 **사람이 직접 작성** — Claude는 스캐폴딩/마크업까지만.
> 3. 루트 `privacy.html` 경로 변경 금지 (스토어 등록 URL).
> 4. `server/` (블로그 VPS SSR) 는 건드리지 않는다.

---

## 0. 현황 진단 (라이브 실측 vs 지시서)

### ✅ 이미 되어 있음 (작업 불필요)
- AdSense 코드 설치 완료 — `index.html:9,16`, `devlog.html:13` (client `ca-pub-1576424722880428`)
- `ads.txt` 정상 — `google.com, pub-1576424722880428, DIRECT, ...`
- `robots.txt` 정상 — `Allow: /`

### ❌ 깨진 링크 (지시서 TASK 1-1 + 추가 발견)
| 위치 | 링크 | 상태 |
|---|---|---|
| `index.html:724` | nav 브랜드 `href="#"` | 빈 링크 |
| `index.html:837` | Play 스토어 열기 `href="#"` | 빈 링크 |
| `index.html:886` | 개발 로그 보기 `href="#"` | 빈 링크 |
| `index.html:921` | 기능 명세 보기 `href="#"` | 빈 링크 |
| `index.html:1155` | 푸터 GitHub `href="#"` | 빈 링크 |
| `index.html:1156` | 푸터 X/Twitter `href="#"` | 빈 링크 |
| `devlog.html:171-172` | 푸터 GitHub / X `href="#"` | 빈 링크 |
| **★ `index.html:834`** | `./privacy/self-check-study.html` | **404 (폴더 없음)** |
| **★ `index.html:883`** | `./privacy/make-money.html` | **404 (폴더 없음)** |
| **★ `index.html:918`** | `./privacy/googsky.html` | **404 (폴더 없음)** |
| **★ `index.html:1148`** | 푸터 `./privacy/` | **404 (폴더 없음)** |

> ★ = 지시서에 없던 추가 발견. 루트 `privacy/` 폴더가 아예 없어 앱 카드 Privacy 링크 4개가 전부 404.
> 소스는 `design/template-editorial-v2/privacy/` 에 존재 (index/self-check-study/make-money/googsky + _styles.css).

### ❌ 필수 페이지 미비
- **About 독립 페이지 없음** — nav `About`(`index.html:733`)는 `#about` → 푸터(`index.html:1122`)로만 점프. 실제 소개 페이지 부재.
- **Privacy 광고문구 전무** — `privacy.html` 에 Google/쿠키/DoubleClick/adssettings 고지 없음 (현 섹션: 수집목적/항목/기간/제3자/아동/권리/책임자/변경).
- **sitemap.xml 없음**.

### ⚠️ 이메일 불일치
- `index.html:1157` → `woohoo.dew1017@gmail.com`
- `devlog.html:173` → `dev@b-lot.co.kr`
- 대표 메일 1개로 통일 필요. **(결정 필요)**

### ⚠️ 심사기간 블로그 격리 대상
- `index.html:732` nav `세상만사 ↗` → `blog.woo-hoo.kr`
- `index.html:949` Now building 티커 내 blog 링크
- `index.html:1145` 푸터 `세상만사 구경만사 ↗`

### ⚠️ devlog 구조 / 콘텐츠
- 현재 `devlog.html` = 단일 타임라인 3개 엔트리(각 100~200자 메모). `index.html:986` `#devlog` 미리보기 3개.
- 개별 URL 페이지(`/devlog/{slug}`) 없음 → 실질 페이지 수로 안 잡힘.
- 1,000자 이상 완성글 12~15개 필요 (본문은 사람 작성).

---

## 🔑 결정 완료 (2026-06-07 사용자 확정)
- [x] **D1. 대표 이메일** → `woohoo.dew1017@gmail.com` 로 전부 통일
- [x] **D2. Play 스토어 버튼** → "출시 예정 · 심사중" 비활성 표기
- [x] **D3. GitHub / X 계정** → 링크 삭제
- [x] **D4. 앱별 Privacy** → 카드 링크를 루트 `privacy.html` 로 통합 (`privacy/` 폴더 생성 안 함)
- [x] **D5. devlog 라우팅** → 정적 `/devlog/slug.html` 확정

---

## PHASE 1 — 신뢰성/구조 정비 ✅ 완료
- [x] 1-1a. `index.html` 빈 `href="#"` 처리 — brand→`/`, Play→출시예정, 개발로그/기능명세→`./devlog.html`, GitHub/X 삭제
- [x] 1-1b. `devlog.html` 푸터 빈 링크 + nav 깨진 앵커(`#products`/`#download`) 정정
- [x] 1-1c. ★ 앱별 Privacy 404 해소 — 카드 3개 + 푸터 2곳 모두 `./privacy.html` 로 통합
- [x] 1-2. About 독립 페이지 `about.html` 신설 + index/devlog nav·푸터에서 연결
- [x] 1-3. 이메일 통일 → `woohoo.dew1017@gmail.com` (index/devlog/about/privacy 일치)
- [x] 1-4. `privacy.html` 에 애드센스 광고/쿠키 고지 + 제3자 링크 면책 섹션 추가
- [ ] 1-5. (선택·보류) `terms.html` 간단 면책/저작권 페이지
- [x] 1-6. 블로그 링크 격리 — nav/티커/푸터 3곳 `rel="nofollow"` (승인 후 원복)
- [x] 1-7. `sitemap.xml` 생성 + `robots.txt` 에 Sitemap 명시

## PHASE 2 — devlog 구조화 ✅ 완료
- [x] 2-1. `/devlog/{slug}.html` 개별 페이지 + 공유 스타일 `devlog/_post.css` + `devlog.html` 인덱스 연결
- [x] 2-2. 글 구조: 제목/작성일/태그칩/본문/이전·다음 글 네비
- [x] 2-3. 기존 메모 3편 개별 페이지화 — `stamp-interaction` / `persona-pipeline` / `stability-score`
- [x] 2-4. 내부 링크 — 각 글 → `#projects` 관련 프로젝트 콜아웃 + 하단 "다른 개발기 보기"
- [x] (추가) `index.html` `#devlog` 미리보기 3개 + sitemap.xml 에 개별 글 반영
- [ ] ⚠️ 본문은 현재 메모 요약 수준 — PHASE 3 에서 각 1,000자+ 로 확장 (사용자 작성)

## PHASE 3 — 콘텐츠 채우기 (본문은 사람 작성)
> Claude: 스캐폴딩 완료. **본문(각 1,000자+)은 사용자가 작성.**
> draft = `noindex` + sitemap 제외 + 인덱스 미연결. 본문 채우면 발행 절차 진행.
- [x] 스캐폴딩 — 총 15편 자리 확보(발행 3 + draft 12), 각 글에 5단계 작성 가이드(주석) 삽입

### 발행 완료 (본문 메모 수준 → 확장 권장)
| slug | 제목 | 프로젝트 | 상태 |
|---|---|---|---|
| publish-queue-spacing | 30분 큐 분산 + AI양산 위험 | money | ✅ 발행(본문 ~1,000자, DB 실제 누수 사례 id=208 인용) |
| v2-redesign | v2 리디자인 — 회사사이트를 버린 이유 | 회고 | ✅ 발행(~800자, 디테일 보강 여지) |
| stamp-interaction | 도장 마이크로 인터랙션 | self | ✅ 발행(짧음) |
| persona-pipeline | 페르소나 5종 동시 생성 | money | ✅ 발행(짧음) |
| stability-score | 안정·적정·도전의 경계 | googsky | ✅ 발행(짧음) |

### draft (본문 작성 대기 — noindex)
| slug | 제목 | 프로젝트 | 본문 |
|---|---|---|---|
| user-test-once-more | “한 번 더” 만든 0.4초 — 유저테스트 | self | [ ] |
| kakao-og-image | 카톡 OG 이미지 튜닝 삽질기 | self | [ ] |
| play-store-review | Play 스토어 심사 통과까지 | self | [ ] |
| crawler-robots-block | 크롤러와 robots.txt 차단 | money | [ ] |
| tistory-oauth-refresh | 티스토리 OAuth 자동 복구 | money | [ ] |
| grade-data-normalize | 등급 데이터 정규화 | googsky | [ ] |
| parent-interview | 학부모 인터뷰 8건 | googsky | [ ] |
| solo-three-apps | 앱 3개 동시 운영 — 우선순위 | 회고 | [ ] |
| coding-with-claude | Claude 코딩 좋았던/안통한 것 | 회고 | [ ] |
| side-project-infra | 인프라 — 도메인·배포·비용 | 회고 | [ ] |

### 글 발행 절차 (본문 작성 후, 글마다)
1. `<head>` 의 `<meta name="robots" content="noindex">` 제거
2. 본문 작성 가이드 주석 + `.post-draft` 배너 삭제, 작성 예정 날짜를 실제 날짜로
3. `devlog.html` 인덱스 + (필요시 `index.html` `#devlog`)에 항목 추가
4. `sitemap.xml` 에 URL 추가, 이전·다음 글 네비 연결
> 본문이 채워지는 대로 위 1~4를 Claude 가 대행 가능(요청 시).

## PHASE 4 — 최종 점검 후 신청
- [ ] devlog 완성글 12+ / 각 1,000자+ / 개별 URL 확인
- [ ] About·Privacy(광고문구)·Contact 정상 동작
- [ ] 빈 `#` 링크 0개, 404 0개 (privacy 포함)
- [ ] 모바일 반응형 깨짐 없음
- [ ] 블로그 링크 격리 적용 확인
- [ ] `blog.woo-hoo.kr` 광고 코드 없음 확인
- [ ] sitemap.xml 정상 / AdSense 코드 `<head>` 설치 확인
- [ ] AdSense 콘솔에서 `woo-hoo.kr` 검토 요청

---

## 작업 순서 권장
`결정(D1~D5) → PHASE 1 → PHASE 2 → PHASE 3 스캐폴딩 → (사용자 본문) → PHASE 4`
PHASE 1 은 결정만 나오면 Claude 단독으로 일괄 처리 가능. PHASE 3 본문이 일정상 최장 구간.
