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
- **#3 라우팅(Cloudflare/DNS)** — ❓ 미정. 두 경로 중 택1:
  - **(A) 스펙 권장 — 무위험:** DNS 는 GitHub Pages 유지 + Cloudflare Origin Rule 로 `woo-hoo.kr/blog/*` 만 이 웹서버로. `privacy.html` 등은 GitHub Pages 가 계속 서빙(0 리스크).
  - **(B) VPS 단일 origin:** DNS 를 이 서버로 돌리고 nginx 가 정적+`/blog` 모두 서빙. 이 경우 `/home/www/woo-hoo.kr/html` 에 현행 정적(특히 `privacy.html`)이 반드시 존재해야 함.
- **og:image** — 페르소나별 대표 그래픽 미생성(현재 텍스트 카드). 추후 이미지/SVG 엔드포인트로 보강.
