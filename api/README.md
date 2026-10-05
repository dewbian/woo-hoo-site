# woohoo-journal-api

PWA 폼(`/write/`)의 **글 + 사진** POST 를 `journal/entries/*.json` + `journal/assets/*.webp` 로 저장하고
`git push` → GitHub Action(`rebuild-journal.yml`)이 `journal.html` 재생성·배포한다.

```
[PWA 폼 /write/] --POST(Bearer)--> [nginx /api/journal] --> [이 서비스 :8011] --> git push --> Action --> 배포
```

## VPS 설치 (ssh woohoo, root)

> spick(:8000)·blog 유닛/nginx 블록은 건드리지 않음. 새 포트 8011·새 유닛·woo-hoo.kr 블록 location 만 추가.

```bash
# 1) repo clone (api 전용 — docroot 와 분리)
cd /home/www/woo-hoo.kr
git clone https://github.com/<OWNER>/woo-hoo-site.git journal-api
cd journal-api
git remote set-url origin https://x-access-token:<GH_PAT>@github.com/<OWNER>/woo-hoo-site.git
git config user.name  "woohoo-journal-api"
git config user.email "api@woo-hoo.kr"
git checkout main

# 2) 의존성 (sharp 네이티브 — 필요시 apt install -y build-essential)
cd api
node -v    # >=18
npm ci --omit=dev   # 또는 npm install --omit=dev

# 3) .env (secret — 커밋 금지)
cp .env.example .env
nano .env          # JOURNAL_TOKEN(=openssl rand -hex 32), REPO_DIR, PORT=8011
openssl rand -hex 32   # 토큰 생성용

# 4) systemd
cp woohoo-journal-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now woohoo-journal-api
curl -s 127.0.0.1:8011/api/journal/health   # {"ok":true}
journalctl -u woohoo-journal-api -f
```

## nginx — woo-hoo.kr 블록에 추가

`http {}` 블록(레이트리밋 존):
```nginx
limit_req_zone $binary_remote_addr zone=journal_api:10m rate=6r/m;
```

`server { server_name woo-hoo.kr ...; }` 블록(정적 docroot 서빙하는 기존 블록):
```nginx
# PWA 입력 엔드포인트 — POST 전용 + 레이트리밋 + 실 IP 전달
location = /api/journal {
    limit_except POST { deny all; }
    limit_req zone=journal_api burst=3 nodelay;
    client_max_body_size 12m;
    proxy_pass http://127.0.0.1:8011;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```
적용: `nginx -t && systemctl reload nginx`. (폼 `/write/` 는 기존 정적 서빙으로 자동 노출 — robots `Disallow: /write/` + 페이지 `noindex`.)

## 보안 체크
- `JOURNAL_TOKEN` 랜덤 길게, URL 아닌 Authorization 헤더로만. `.env`·git remote URL 외 노출 금지.
- POST-only + nginx 레이트리밋. 이미지만 허용(sharp 디코드 실패=제외), 파일명 서버생성, EXIF/GPS 제거.
- 배포 후 `bash ~/.claude/rules/sec-check.sh https://woo-hoo.kr` 통과 확인.

## 코드 갱신 시
```bash
cd /home/www/woo-hoo.kr/journal-api && git pull
cd api && npm ci --omit=dev && systemctl restart woohoo-journal-api
```
