# woo-hoo.lab — Template Snapshot

이 폴더는 **woo-hoo.kr** 사이트의 디자인 시스템 + 마크업 스냅샷을 템플릿으로 보관한 것입니다.
다른 프로젝트나 후속 리디자인의 출발점으로 재사용하기 위해 만들어졌습니다.

- **스냅샷 일자:** 2026-05-23
- **컨셉:** "1인 실험실 · 엔지니어 저널" (Editorial Engineer's Journal)
- **출처:** `D:/bhs-project/woo-hoo-site/` 루트의 동일 파일들을 그대로 복사

## 포함 파일

| 파일 | 역할 |
|---|---|
| `index.html` | 싱글 페이지 (히어로 → 실험실 그리드 → 지금 만드는 중 → 개발로그 미리보기 → 다운로드&구독 → 푸터) |
| `devlog.html` | 별도 개발 로그 타임라인 페이지 |
| `privacy.html` | 개인정보처리방침 (스토어 등록용 공개 URL용) |
| `apps/self-check-study.html` | 셀프체크 스터디 앱 상세 소개 페이지 (서브 페이지 패턴 예시) |
| `apps/self-check-study/` | 위 페이지가 쓰는 에셋 — 아이콘·피처 그래픽·스크린샷 5장 |
| `styles.css` | 공유 디자인 시스템 — CSS 변수, 컴포넌트, 모션, 에디토리얼 컴포넌트 |
| `favicon.svg` | 브랜드 스마일 파비콘 |

## 디자인 시스템 요지

- **타이포 4-패밀리 스택**
  - 본문: **Pretendard** (한·영 공통)
  - 한글 디스플레이: **Black Han Sans** — 헤비 컨덴스드, 큰 헤드라인
  - 영문 디스플레이/라벨: **Fraunces** 이탤릭 — 챕터 마커, 영문 강조
  - 모노: **JetBrains Mono** — 기술 라벨, 파일 경로
  - 손글씨: **Nanum Pen Script + Gaegu** — 주석/마커 노트
- **컬러**: 페이퍼 `#f4f1ea` 베이스, 잉크 `#111`, 비비드 액센트(블루/핑크/옐로/그린/스카이). 히어로는 그라디언트 메시.
- **에디토리얼 컴포넌트**: `.chapter` (§ 01 형식), `.path` (파일경로 표시 + blinking cursor), `.marginalia` (우측 주석 노트), `.tape` (테이프 라벨 CTA), `.stamp` (도장 스타일 상태 배지), `.marker-draw` (헤드라인 마커 self-draw).
- **모션 레이어**: scroll reveal + sequence, marquee, owl 눈동자 커서 추적, 클릭 pop(woo!/hoo!/✶), 드래그 스티커, 떠다니는 doodle, 진행도 바 채움. `prefers-reduced-motion` 가드 포함.
- **배경**: 모눈종이(랩 노트) 격자 + 노이즈 그레인 오버레이.

## Placeholder (재사용 시 교체)

- 셀프체크 스터디 App Store / Google Play 링크
- make-money / googsky 외부 링크 또는 GitHub 레포
- GitHub / X 프로필 URL
- Formspree 폼 endpoint (`action="https://formspree.io/f/XXXXXXXX"`)
- OG 이미지 (`og.png` 1200×630 추가 필요)

모두 HTML 안에 `<!-- TODO: ... -->` 주석으로 표시되어 있습니다.

## 라이브 버전과의 관계

`/design/template/` 는 **스냅샷(보관용)** 입니다. 실제 배포는 프로젝트 루트의 동일 파일들이 GitHub Pages로 호스팅됩니다(`woo-hoo.kr`). 이 폴더의 파일은 직접 호스팅되지 않습니다 — 참조·재사용용입니다.
