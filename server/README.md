# 세상만사 구경만사 — woo-hoo.kr 블로그 서버

make-money 가 Supabase `articles` 에 쌓는 LLM 뉴스 글을 woo-hoo.kr `/blog` 에 **동적 SSR** 로 게시한다.
설계 전문: [`../docs/superpowers/specs/2026-05-28-woohoo-blog-news-design.md`](../docs/superpowers/specs/2026-05-28-woohoo-blog-news-design.md)

> **불변 제약:** make-money 코드/DB 미수정(읽기 전용), 루트 `privacy.html`·CNAME URL 변경 금지.

## 구조
```
server/
├── main.py            FastAPI 앱·라우트 (/blog, /blog/{id}, sitemap.xml, feed.xml)
├── blog.py            Supabase 읽기 + 제목/요약/HTML 파생 + TTL 캐시
├── templates/         base/list/detail/404/503 (Jinja2, 라이브 v2 헤더·푸터 계승)
├── static/blog.css    v2 디자인 토큰 인라인 사본 + 블로그 컴포넌트
├── tests/             파생 함수 단위 테스트 (pytest)
├── requirements.txt   런타임 의존성
└── .env.example       환경변수 템플릿
```

## 라우트
| 경로 | 설명 |
|---|---|
| `GET /blog` | 목록(최신순) · `?page=N` · `?angle=페르소나` 필터 |
| `GET /blog/{id}` | 글 상세 (마크다운→HTML + 애드센스 + OG) · 미존재/미완료 → 404 |
| `GET /blog/sitemap.xml` | 발행 글 sitemap |
| `GET /blog/feed.xml` | RSS 2.0 |

## 로컬 실행
```bash
cd server
python -m venv .venv
.venv/Scripts/activate           # Windows (Linux/mac: source .venv/bin/activate)
pip install -r requirements-dev.txt
cp .env.example .env             # 값 채우기 (SUPABASE_URL/KEY 등)
uvicorn main:app --reload --port 8000
# → http://127.0.0.1:8000/blog
```
`.env` 의 Supabase 자격이 없으면 모든 페이지가 503(서비스 불가)으로 안전 처리된다.

## 테스트
```bash
cd server
.venv/Scripts/python -m pytest -q
```

## 배포 (GitHub Actions → 준비된 웹서버)
`server/**` push 시 `.github/workflows/deploy.yml` 가 SSH 로 동기화→설치→재시작한다.

**필요한 레포 Secrets:**
| Secret | 예시/설명 |
|---|---|
| `SSH_HOST` | 웹서버 호스트/IP |
| `SSH_USER` | SSH 계정 |
| `SSH_KEY` | 배포용 개인키 전체 |
| `SSH_PORT` | (선택) 기본 22 |
| `DEPLOY_PATH` | 앱 배치 경로 — **public html 밖** 권장. 예: `/home/www/woo-hoo.kr/server` |

> 로컬에서 `ssh woohoo` → `/home/www/woo-hoo.kr/html` 이 **웹 루트(정적)** 다.
> 파이썬 앱은 보안상 그 안이 아니라 **형제 경로**(`/home/www/woo-hoo.kr/server`)에 두고, nginx 가 `/blog` 만 프록시한다.
> `~/.ssh/config` 의 `woohoo` alias 는 로컬 전용이라 Actions 에서는 못 쓴다(위 Secrets 로 분리).

### 서버 1회 세팅
1) 앱 환경변수: `DEPLOY_PATH/.env` 작성(`.env.example` 참고). rsync `--delete` 에도 보존됨.
2) systemd 유닛 `/etc/systemd/system/woohoo-blog.service`:
```ini
[Unit]
Description=woo-hoo.kr blog (FastAPI)
After=network.target

[Service]
WorkingDirectory=/home/www/woo-hoo.kr/server
EnvironmentFile=/home/www/woo-hoo.kr/server/.env
ExecStart=/home/www/woo-hoo.kr/server/.venv/bin/gunicorn main:app \
  -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000 --workers 2
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now woohoo-blog
```
3) nginx — `/blog` 만 파이썬으로 프록시(나머지는 기존 정적/GitHub Pages 유지):
```nginx
location /blog {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## 미결 / 확인 필요 (배포 전)
- **#1 AdSense publisher ID** — ✅ 해결: `ca-pub-5717185295429908` (레포 `ads.txt`/`index.html` 과 동일). 인아티클 슬롯 ID 는 미정(`ADSENSE_SLOT_INARTICLE`, 비우면 자동광고만).
- **#2 웹서버** — ✅ 확보: `ssh woohoo`, 웹 루트 `/home/www/woo-hoo.kr/html`. Actions 용 host/user/key Secret 등록만 남음.
- **#3 라우팅(Cloudflare/DNS)** — ✅ **결정: (A) GitHub Pages 유지 + Cloudflare Origin Rule.**
  GitHub Pages 가 메인 origin 으로 모든 정적(`/`, `privacy.html`, `apps/` …)을 계속 서빙하고,
  Cloudflare 가 `woo-hoo.kr/blog/*` 요청만 VPS origin 으로 보낸다. `privacy.html`·CNAME 0 리스크.
- **og:image** — 페르소나별 대표 그래픽 미생성(현재 텍스트 카드). 추후 이미지/SVG 엔드포인트로 보강.

## 라우팅 (A) 설정 절차 — Cloudflare
> 앱 코드는 `/blog/*` 를 그대로 처리하므로 변경 불필요. 아래는 외부(대시보드/서버) 설정만.

1. **DNS 를 Cloudflare 로 이관** — woo-hoo.kr 네임서버를 Cloudflare 로 변경(이미 GitHub Pages 용 CNAME/A 레코드는 그대로 import). 기본 origin = GitHub Pages 유지.
2. **VPS origin 준비** — VPS 가 Cloudflare 에서 도달 가능한 공개 호스트명(예: `origin.woo-hoo.kr`, **DNS-only/회색 구름**)이 필요. nginx 443 + **Cloudflare Origin Certificate**(무료) 로 TLS, SSL/TLS 모드 **Full**.
3. **Origin Rule 추가** (Cloudflare → Rules → Origin Rules): 조건 `Hostname=woo-hoo.kr AND URI Path starts with /blog` → **Origin 을 VPS 호스트**로 override. 나머지 경로는 규칙 미적용 → GitHub Pages.
4. **전환 안전 확인**(스펙 7.3): 적용 직후 `/`, `/privacy.html`, `/apps/` 가 정상 200 인지 먼저 확인 → 그 다음 `/blog`, `/blog/<id>` 동작 확인.

## 남은 사람-손 작업(코드 외)
- GitHub 레포 **Secrets** 등록: `SSH_HOST` `SSH_USER` `SSH_KEY` `DEPLOY_PATH`(+선택 `SSH_PORT`).
- VPS 1회 세팅: `DEPLOY_PATH/.env` 배치, systemd 유닛 등록, nginx `/blog` 프록시(위 참조).
- Cloudflare: DNS 이관 + Origin Rule(위 (A) 절차).
- (선택) AdSense 인아티클 슬롯 ID → `ADSENSE_SLOT_INARTICLE`.
