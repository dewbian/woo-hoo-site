# 작업 핸드오프 (index9.html 인터랙션)

작성: 2026-09-18 (KST) · 계정 전환 대비 컨텍스트 보존용

## 지금까지 (파일: `design/template-editorial-v3/index9.html`, 테스트/미배포)
스크롤 배경전환(방법1: IntersectionObserver + `html` bg transition)
색 흐름: 히어로(다크 #100e0d) → S1(라이트핑크 #fb96ba) → S2(액센트 #f76b9f) → S3(라이트핑크 #fb96ba) → FAQ(서페이스 #f8ead7) → 풋터(다크)

### S1 (라이트핑크) — 핀 스크럽 타이포 + 인터랙티브 도트 (완료)
- 문구 1~4 벽돌 계단식(크기·들여쓰기 제각각) 순차 등장 → 헤드라인 "말하면 바로 / 통하는 파트너" 갈라짐 + 중앙 이미지(card1) scale 0.15→ 확대
- 배경 인터랙티브 도트(커서 근접 확대·밝기·밀림), 글자·이미지 커서 미세 시차

### S2 (액센트) — 키네틱 타입 릴 5씬 (완료, 레퍼런스: kinetic-type-reel)
- 씬1~4: 대형 문구(만드는 과정을/공유하는 1인 스튜디오[아웃라인]/기획 이해력과 감각적인 개발로/움직이는 서비스만 올립니다[잉크]) + 배경 초대형 워드(PROCESS/STUDIO/CRAFT/SHIP) 크로스페이드, 커서 시차. **글자색 전부 흰색.** 폰트 S1과 동일(`"Archivo",system-ui` → 한글 시스템폰트)
- 씬5(파이널) 스크럽 시퀀스: 텍스트 "개인 실험실, / 유쾌하게 완성되는 프로젝트" 완전 등장 → **가독 체류** → 하트풍선 **순차 뿅뿅뿅**(4종 heart-holo/glossy/heart3/heart4, 26개, 중앙 밀집) → 선물상자(gift.png) 중앙 등장·오래 체류 → 풍선 위로 순차 흩어져 소멸 → 선물 단독 홀드
- 파이널 타임라인(fp=파이널 스크럽 진행도): textOp fade 0.56~0.74 / pop st=0.38+o*0.30 / gift 0.62~0.78 / scatter sst=0.72+o*0.10 / track 780vh
- 에셋: `assets/s2/gift.png`(투명 원본), heart-holo·heart-glossy·heart3·heart4(누끼=scipy 연결요소로 체커배경 제거)
- HUD·코너 라벨·풍선다발은 제거됨

## S3 (라이트핑크) — 완료 (2026-09-18)
레퍼런스: `haoqi-portfolio-interaction-sample.html` 의 `.contact h2 .line`(라인 마스크 리빌: overflow hidden + inner span translateY 상승) 기법 채택.

구현:
- 문구 6줄 라인 리빌 = **haoqi `.contact h2 .line` "Let's make" 순수 마스크 슬라이드업 재현**(opacity 페이드 없음). 래퍼 `.s3-ln{overflow:hidden}` + inner `span{translateY(105%)}` → `.s3.in` 시 `translateY(0)`, `transition:transform 1s cubic-bezier(.19,1,.22,1)`(=expo.out). stagger는 CSS `transition-delay` (1~6줄 = 0/.2/.4/.6/.8/1.0s). 뷰 진입 시 IntersectionObserver(threshold .35, once)로 `in` 부여 → **한 번 등장 후 유지**.
  - 1~4: 설명 카피(작은 크기), 5~6(`.s3-big`): "탄탄한 기술력"/"막힘없는 직통 소통" 더 크게(clamp 28~54px, weight 900).
- 레이아웃(구성 결정): **좌측 컬럼 = 카피 6줄 + 인포그래픽 플레이스홀더**(점선 카드 `이미지 수령 후 교체 예정`), **우측 컬럼 = 회전 뒤광(`.s3-rays` conic-gradient screen blend, spin 24s) + 흔들리는 디스코볼**(`.s3-ball` sway ±5deg 6.5s, transform-origin 상단=체인). 모바일(≤820px)은 1컬럼, 디스코볼 위로.
- 에셋: `assets/s3/discoball.png` — 원본 `크몽 이미지/5f7428…jpg`(핑크·골드 미러볼, 체커=투명표시 배경) 누끼. scipy 테두리 연결 배경(밝기>200 & 채도<26)만 제거 → 내부 스파클/골드체인 보존, bbox 크롭(559×967).
- reduced-motion: 리빌 즉시 표시 + 회전/흔들림 정지.
- 검증: Playwright 데스크톱(1440)·모바일(390) 스크린샷 확인, 6줄 opacity 1 도달, 콘솔 에러 favicon 404뿐(무해).

**남은 것**: 인포그래픽 실제 이미지 수령 시 `.s3-info` 플레이스홀더 교체. 여전히 미배포(design/ 테스트 소스).

## 배포/서버
- 프로덕션은 루트 `index.html` (이미 배포됨, main push=자동배포). index9는 design/ 이라 미배포(테스트 소스)
- 로컬 확인: 프로젝트 루트에서 `python -m http.server 8899` → `http://localhost:8899/design/template-editorial-v3/index9.html`

## 재개 방법
`claude --resume` (세션 목록) 또는 `claude -c`. 세션 유실 시 이 파일 기준으로 S3부터 이어가면 됨.
