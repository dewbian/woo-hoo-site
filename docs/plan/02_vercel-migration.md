# 02 — woo-hoo.kr 자체 서버(cafe24 VPS nginx) → Vercel 이전

- 작성: 2026-11-14 (KST) · 상태: 검토 2차 반영(r2) · 승인 전
- **변경(2026-11-14, 사용자 결정): 저널 입력 기능 폐기.** `/write` PWA·`/api/journal`·`lib/journal`·package.json 삭제, journal.html은 기존 글 그대로 정적 유지. 아래 3.2·3.3 및 저널 관련 DoD·env·`journal-preview` 브랜치는 무효. 남은 범위 = 정적 사이트 이전 + 헤더 + 도메인 + 워크플로 정리.
- 기준 사례: account-book(2026-11-10), googsky(2026-11-14) 이전. 공통 절차는 `account-book/doc/plan/03_vercel_migration_playbook.md`.

## 1. 목표 · 범위

`git push main` → Vercel 자동배포로 woo-hoo.kr 정적 사이트 + 저널 입력 API를 운영하고, VPS 의존을 없앤다.

| 구성 | 현재 | 이전 후 | 범위 |
|---|---|---|---|
| 정적 사이트 (루트 HTML·assets·journal·watch·devlog·apps·write PWA 등) | nginx docroot `/home/www/woo-hoo.kr/html`, `deploy-static.yml` rsync | Vercel 정적 서빙 | 포함 |
| `/api/journal` (PWA 글+사진 → repo 커밋) | Node express :8011, 로컬 clone에 파일 쓰고 `git push` | Vercel Node 함수, **GitHub Git Data API**로 커밋 | 포함(재작성) |
| `write/app.js` 이미지 인코딩 | `toBlob('image/webp')` — iOS Safari는 PNG로 대체됨 | webp 미지원 시 JPEG 0.8로 재인코딩 | 포함(소규모 클라 수정) |
| `/blog` FastAPI (`server/`) | `woohoo-blog` 서비스 disabled, 현재 502. `blog.woo-hoo.kr` DNS 없음 | 이전 안 함 → Vercel에서 404 | **제외**(사용자 결정 2026-11-14) |
| journal/watch 재생성 Action | 커밋 후 VPS rsync | 커밋만(배포는 Vercel이 push 감지) | 포함(DNS 전환 후 수정) |

비범위: 블로그 복구, 디자인/콘텐츠 변경, CSP 강제 모드(Report-Only까지만).

## 2. 현재 구성 사실 (2026-11-14 서버·저장소 실측)

- nginx `woo-hoo.kr`/`www.woo-hoo.kr`: `/blog` → :8001 프록시(죽음), `= /api/journal` POST-only + `limit_req 6r/m burst 3` + `client_max_body_size 12m` → :8011, 나머지 `try_files $uri $uri/ =404`.
- `www.woo-hoo.kr`, `blog.woo-hoo.kr`: 공용 DNS 응답 없음.
- 서비스: `woohoo-journal-api`(running), `woohoo-blog`(disabled). spick 유닛·nginx 블록은 이미 없음.
- `jobkorea/`(이력서 PDF)·`인터랙션요청.txt`는 gitignore·미추적 → Git 연동 배포로는 업로드되지 않음. 로컬 `vercel` CLI 배포 시에만 위험.
- 내부 `/blog` 링크 없음. `sameAs: https://blog.woo-hoo.kr`만 `index.html`·`showroom.html`·`llms.txt`에 남음(DNS 없는 도메인).
- 클라이언트(`write/app.js`): ≤1200px 리사이즈 후 최대 4장 FormData POST, `Authorization: Bearer`, 응답 `{url}` 사용, 401/비정상 상태코드 표시.

## 3. 설계

### 3.1 저장소 구조
- `api/`에는 **`api/journal.js` 하나만** 둔다(Vercel은 `api/` 아래 모든 `.js`를 함수로 만든다). 헬퍼는 `lib/journal/*.js`(api 밖).
- 기존 `api/server.js`·`woohoo-journal-api.service`·README·`.env.example`·`.gitignore`·`package.json`은 **이동하지 않고** `.vercelignore`로 배포에서 제외(VPS 유닛이 `journal-api/api/server.js`를 직접 실행하고 POST마다 `git pull` → 이동하면 재시작 시 VPS API·롤백 경로가 깨짐). VPS 정리(4단계 7) 후 삭제.
- `lib/journal/*.js`·테스트는 정적 파일로 공개되지만 저장소 자체가 public이라 추가 노출 없음(수용).
- 루트 `package.json`(신규, `"private": true`, `"type": "module"`, `"engines": {"node": "22.x"}`), **scripts 없음**(Preset Other에서 build 스크립트가 실행되지 않게). 의존성 `busboy`, `sharp`.
  - lockfile은 Linux용 sharp 바이너리가 빠지지 않게 생성(`npm i --os=linux --cpu=x64 sharp`) 또는 Vercel 설치에 맡기고 Windows lockfile의 optional deps 누락 여부를 Preview에서 확인.
- `.vercelignore`(api 레거시 제외는 필수, 나머지는 CLI 배포 대비 방어): `api/server.js api/package.json api/package-lock.json api/README.md api/*.service api/.env.example api/.gitignore .github .claude .gstack .superpowers .design-kit .playwright-mcp server docs design jobkorea legacy scripts README.md CNAME CLAUDE.md 인터랙션요청.txt *.py`. `package.json`/lockfile은 함수 설치에 필요하므로 제외하지 않음(공개돼도 위험 낮음).
- 운영 규칙: Production 배포는 Git push로만(`vercel --prod` CLI 금지).
- `vercel.json`: `regions: ["hnd1"]`, `cleanUrls: false`(기존 `.html` URL 유지), `redirects: [{source: "/write", destination: "/write/", permanent: true}]`(상대경로 `./app.js` 보호), `headers`(3.4), `functions: {"api/journal.js": {"maxDuration": 30}}`.
- Vercel 설정: Framework Preset = Other, Build Command 비움, Output Directory = 루트.

### 3.2 `/api/journal` 함수 (계약은 기존과 동일)
- 요청: `POST multipart/form-data` (`title`, `body`, `kind`, `images` ≤4), `Authorization: Bearer`. 그 외 메서드 405.
- 응답: 200 `{ok, url, kind, images}` / 401 `{error:"UNAUTHORIZED"}` / 400 `{error:"EMPTY"}` / 405 / 500 `{error:"INTERNAL"}`. 4.5MB 초과는 **플랫폼이 함수 실행 전 413**으로 거절(코드 응답 아님) — 클라는 "실패 (413)" 표시.
- 순서: ① 토큰 constant-time 비교(본문 파싱 전, 실패 시 GitHub 호출 없음) ② `req.body`를 건드리지 않고 `req.pipe(busboy)` 스트리밍 파싱(파일 ≤8MB·≤4개) ③ sharp `rotate→resize 1200→webp q80`(EXIF 제거, 디코드 실패 이미지 제외) ④ entry JSON(KST id/datetime, 기존 `kstParts` 그대로) — id = `<stamp>-<kind>-<4자리 랜덤hex>`, 이미지 파일명도 `<id>-<n>.webp`(기존 `<stamp>-<n>`은 같은 초 다른 글끼리 덮어씀). `build_journal.py`는 entries glob + datetime 정렬이라 형식 변경 영향 없음(검토 확인).
- **GitHub 커밋 (Git Data API)**:
  1. `GET /repos/{repo}/git/ref/heads/{branch}` → `headSha`
  2. `GET /repos/{repo}/git/commits/{headSha}` → `baseTreeSha = .tree.sha` (커밋 sha 아님)
  3. 파일별 `POST /git/blobs` (webp는 base64, JSON은 utf-8) → blob sha
  4. `POST /git/trees {base_tree: baseTreeSha, tree:[{path, mode:"100644", type:"blob", sha}]}`
  5. `POST /git/commits {message, tree, parents:[headSha], author}`
  6. `PATCH /git/refs/heads/{branch} {sha: newCommit, force:false}`
  7. 6에서 422(경합) → 1부터 재조회하여 **tree·commit 재생성**(blob은 재사용), 최대 3회 후 500.
- 브랜치 분리: `GITHUB_BRANCH` env. **`VERCEL_ENV !== 'production'`이면 `main`으로의 쓰기를 코드에서 거부**(500 + 로그). Preview는 `journal-preview` 브랜치에 기록.
- env:
  | 변수 | Production | Preview |
  |---|---|---|
  | `JOURNAL_TOKEN` | 기존 값(PWA 저장 토큰 그대로 동작) | 별도 테스트 토큰 |
  | `GITHUB_TOKEN` | fine-grained PAT(repo `dewbian/woo-hoo-site`, Contents R/W, 1년 만료), Sensitive | 같은 PAT 허용(브랜치 가드로 main 차단) |
  | `GITHUB_REPO` | `dewbian/woo-hoo-site` | 동일 |
  | `GITHUB_BRANCH` | `main` | `journal-preview` |
  | `SITE_URL` | `https://woo-hoo.kr` | Preview URL |
  - Preview 배포는 Vercel Authentication(기본 보호) 유지.
- 커밋 작성자: `woohoo-journal-api <api@woo-hoo.kr>`, 메시지 `journal: <title> [web]`. PAT로 push되므로 `rebuild-journal.yml`이 정상 트리거됨(Actions의 `GITHUB_TOKEN` push와 달리).
- 레이트리밋: Hobby에서 WAF 레이트리밋 룰 가용 여부 확인 후 가능하면 `/api/journal` IP당 분당 6회. 불가 시 고엔트로피 토큰이 1차 방어 + 인스턴스 메모리 카운터(보조, best-effort).
- 테스트: `lib/journal`의 kstParts·id 생성·커밋 플로우(GitHub API mock, 422 재시도 포함)·브랜치 가드를 `node --test`로 단위 테스트.

### 3.3 클라이언트 (`write/app.js`)
- `toBlob` 결과 `blob.type !== 'image/webp'`(iOS Safari)면 `image/jpeg` 0.8로 재인코딩. 파일명 확장자도 실제 타입에 맞춤. 서버는 어차피 webp로 재인코딩.
- `write/sw.js`가 앱 셸(`index.html`·`app.js`)을 cache-first로 제공 → **`CACHE`를 `woohoo-journal-write-v2`로 올려** 설치된 PWA가 새 app.js를 받게 함. `app.js`·`index.html`은 network-first로 전환(오프라인 시 캐시).

### 3.4 GitHub Actions
- `rebuild-journal.yml` / `rebuild-watch.yml`: 봇 커밋 메시지에서 **`[skip ci]` 제거**(루프 방지는 paths 필터가 이미 담당, `[skip ci]`는 deploy-static 회피용이었음 → Vercel이 건너뛰지 않도록). 이 변경은 deploy-static가 봇 커밋에도 돌게 하므로 **VPS rsync 스텝 제거·deploy-static 비활성화와 같은 커밋에서, DNS 전환 이후** 적용.
  - DNS 전환 전까지는 기존 워크플로 유지 → VPS도 계속 최신.
- 컷오버 후: `deploy-static.yml`·`deploy.yml` → `on: workflow_dispatch`만(롤백용 수동 실행). rebuild 워크플로 rsync는 삭제 대신 `if: vars.DEPLOY_VPS == 'true'` 플래그로 남김(롤백 시 플래그만 켬). 기존 버그: `rebuild-watch.yml` rsync의 `--exclude 'api'` 누락 — 같은 작업에서 수정.
- Vercel 배포량: 저널 1건 = 커밋 2개(entry + journal.html) = 배포 2회 + watch 봇 커밋. Hobby 일 100회 한도 내. 필요 시 Ignored Build Step으로 `journal/entries`·`watch-notes/`만 바뀐 커밋 스킵(후속).

### 3.5 보안 헤더 (vercel.json `headers`)
- 전 경로: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`(camera/microphone/geolocation/payment/usb 차단). HSTS는 Vercel 기본값 확인(`curl -I`), 없으면 추가.
- CSP **Report-Only**: 인라인 스크립트(gtag·JSON-LD·페이지 스크립트) + AdSense·GTM 출처 → 관측 후 별도 작업에서 강제.
- `/write/sw.js`: `Cache-Control: no-cache`. `manifest.webmanifest` Content-Type `application/manifest+json` 확인.

### 3.6 도메인
- 전환 전: whoisdomain에서 CAA 레코드 유무 확인(있으면 Let's Encrypt 허용), apex TTL을 300으로 낮추고 기존 TTL 시간만큼 대기.
- `woo-hoo.kr`(apex): CNAME 불가 → Vercel Domains 안내 **A 레코드**로 교체(기존 210.114.22.79 삭제). MX/TXT 등은 유지.
- `www.woo-hoo.kr`: Vercel에 추가 + CNAME, apex로 308(현재 DNS 없음, 선택).
- `blog.woo-hoo.kr` 언급(index·showroom `sameAs`, llms.txt 관련 사이트): 사용자 결정으로 제거 완료(2026-11-14).

## 4. 절차

1. 브랜치 `vercel-migration`에서 3.1~3.3·3.5 구현 + 단위 테스트. (3.4 워크플로 변경은 아직 안 함)
2. Vercel 프로젝트 import(사용자): Root=`.`, Preset=Other, env(3.2 표, Production/Preview 구분). `journal-preview` 브랜치를 main에서 생성(없으면 ref 조회 404).
3. Preview 검증: DoD 1~3·5·6 + `/api/journal`로 `journal-preview` 브랜치에 실제 커밋(사진 2장, iOS 4장) 확인.
4. main 머지(사용자 "배포" 지시) → Production 배포, `*.vercel.app`에서 재검증. 이 시점엔 VPS·Vercel 둘 다 main을 따라감.
5. DNS 전환(사용자): CAA·TTL 확인 → apex A 교체 → 4개 네임서버 전부 반영·인증서 확인.
6. 전환 확인 후 별도 커밋: 3.4 워크플로 변경(`[skip ci]` 제거, rsync 플래그화, deploy-static/deploy.yml 수동 전용) → Production `/api/journal` 실제 1건으로 엔드투엔드 확인 후 테스트 글 삭제 여부 사용자 확인.
7. 며칠 후(사용자 승인): VPS `woohoo-journal-api`·`woohoo-blog` 유닛, nginx `woo-hoo.kr`/`blog.woo-hoo.kr` 블록, docroot 정리(account·googsky 정리와 함께). 컷오버 전 서버 `journal-api` clone에 push 안 된 커밋이 없는지(`git log origin/main..`) 먼저 확인.

## 5. Definition of Done

1. 기존 공개 URL 전부 200·동일 내용: sitemap.xml의 모든 URL + 루트 파일(`ads.txt`, `robots.txt`, `sitemap.xml`, `llms.txt`, 사이트 인증 HTML, `favicon.svg`, `og-default.png`) + `/write/`, `/write`(→`/write/` 308). 현 서버 대비 URL 목록 diff 0.
2. 비공개: `/jobkorea/*`, `/docs/*`, `/design/*`, `/server/*`, `/legacy/*`, `/scripts/*`, `/CLAUDE.md`, `/.git/config`, `/.env` → 404.
3. 없는 경로 404(200 HTML 아님), 정적 자산 MIME 정확(manifest 포함).
4. `/api/journal`: 토큰 없음/틀림 401, GET 405, 빈 입력 400, 정상 POST(사진 2장 / iOS 사진 4장) → 대상 브랜치에 entry+webp **1커밋** → (Production) rebuild Action → Vercel 재배포 → `/journal.html` 반영 3분 이내. 저장된 webp에 EXIF 없음. Preview에서 main 쓰기 시도 시 거부.
5. `sec-check.sh https://woo-hoo.kr` FAIL 0 (CSP Report-Only WARN 허용).
6. GA/AdSense 정상 로드, `/write/` PWA 설치·서비스워커 등록 정상, **이미 설치된 PWA가 새 app.js(v2 캐시)로 갱신**.
7. 단위 테스트 통과(kstParts·id·커밋 플로우 422 재시도·브랜치 가드).
8. 롤백 절차(§7) 실행 가능 상태.

## 6. 엣지 · 리스크

| 리스크 | 대응 |
|---|---|
| 비공개 파일 노출 | Git 배포(미추적 파일 미포함) + `.vercelignore` + CLI prod 배포 금지 + DoD 2 실측 |
| iOS 업로드 4.5MB 초과 | 3.3 JPEG 폴백, DoD 4 iOS 4장 실측 |
| sharp Linux 바이너리 누락 | lockfile 생성 방식(3.1) + Preview에서 이미지 POST 실측 |
| 동시 POST 커밋 경합 | non-force ref 업데이트 + tree/commit 재생성 재시도 3회 |
| 같은 초 같은 종류 글 덮어쓰기 | id 랜덤 접미사 |
| Preview가 운영 데이터(main) 오염 | `GITHUB_BRANCH` 분리 + 코드 가드 + 별도 토큰 |
| PAT 유출 시 repo 쓰기 | fine-grained 단일 repo·Contents만·Sensitive·1년 만료 |
| DNS 전환 전 VPS 페이지 노후화 | 워크플로 변경을 DNS 전환 이후로 분리(4단계 6) |
| DNS 전파 중 혼재 | TTL 선조정, 양쪽 모두 같은 main 기준이라 내용 동일, 저널 API도 양쪽이 같은 repo에 커밋 |
| AdSense 수익 사이트의 Hobby(비상업 전제) 약관 | 사용자 판단 필요 — 수익 미미하면 Hobby 유지, 문제 시 Pro 전환. account-book·googsky와 별개로 woo-hoo.kr만 해당 |
| 레거시 api 파일이 Vercel 함수로 인식 | `.vercelignore` 필수 항목, Preview에서 `/api/server` 404 확인 |
| Vercel Hobby 배포 횟수 | 현재 사용량으로 일 100회 내, 필요 시 Ignored Build Step |

## 7. 롤백
- DNS: apex A를 210.114.22.79로 원복(VPS nginx·journal-api는 7단계 정리 전까지 유지).
- 배포: `deploy-static.yml` 수동 실행으로 VPS docroot 동기화, repo 변수 `DEPLOY_VPS=true`로 rebuild 워크플로 rsync 재활성.
- 코드: Vercel Instant Rollback.
