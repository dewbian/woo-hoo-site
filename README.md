# woo-hoo.kr

woo-hoo 앱의 공개 웹사이트 — 앱스토어/구글플레이 등록 시 사용하는 개인정보처리방침 URL 호스팅용.

## 구성

- `index.html` — 루트 랜딩 페이지
- `privacy.html` — 개인정보처리방침 (앱스토어 등록 시 제출 URL)
- `CNAME` — GitHub Pages 커스텀 도메인 설정 (`woo-hoo.kr`)

## 배포

GitHub Pages에서 `main` 브랜치 루트를 정적 호스팅한다.
도메인 `woo-hoo.kr` 의 DNS 레코드는 가비아/도메인 등록기관에서 GitHub Pages IP로 설정한다.

## 공개 URL

- 메인: `https://woo-hoo.kr/`
- 개인정보처리방침: `https://woo-hoo.kr/privacy.html`
