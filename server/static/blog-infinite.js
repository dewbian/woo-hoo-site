// 파일 목적: 블로그 목록(/blog) 무한스크롤 — 다음 페이지 카드 조각을 서버에서 받아 그리드에 이어붙인다.
//   진행 방식: 첫 페이지는 SSR. 하단 sentinel 이 뷰포트에 가까워지면 /blog/cards 로 다음 페이지를 받아 append.
//   '더 보기' 버튼은 JS 비활성 환경의 폴백 링크이자(실제 ?page= 이동), JS 환경에선 수동 로드 트리거로 재사용한다.
//   종료 판단: 첫 SSR 이 내려준 data-total-pages 를 기준으로 하여, 글이 중간에 추가돼도 무한 루프에 빠지지 않는다.

(function () {
  "use strict";

  /**
   * 아직 초기화되지 않은 애드센스 광고 유닛을 찾아 push 한다.
   * SSR 로 박힌 광고와 무한스크롤로 append 된 광고를 동일하게 처리한다.
   * data-ad-pushed 속성으로 자체 중복 push(TagError 'already have ads')를 막는다.
   * (innerHTML 로 삽입된 inline <script> 는 실행되지 않으므로 초기화를 JS 가 전담)
   * @param {ParentNode} [root=document] 광고를 찾을 범위
   * @returns {void}
   */
  function initAds(root) {
    var scope = root || document;
    var ads = scope.querySelectorAll("ins.adsbygoogle:not([data-ad-pushed])");
    for (var i = 0; i < ads.length; i++) {
      ads[i].setAttribute("data-ad-pushed", "1");
      try {
        (window.adsbygoogle = window.adsbygoogle || []).push({});
      } catch (e) {
        /* adsbygoogle.js 미로드/차단 시 무시(로드되면 큐가 처리됨) */
      }
    }
  }

  /**
   * 무한스크롤 초기화. 목록 페이지가 아니거나 더 가져올 페이지가 없으면 아무 일도 하지 않는다.
   * @returns {void}
   */
  function init() {
    // 첫 렌더(SSR)된 목록 광고를 먼저 초기화한다(목록 그리드 유무와 무관하게 시도).
    initAds(document);

    var cards = document.getElementById("cards");
    var infinite = document.getElementById("infinite");
    // 그리드/로더가 없으면(상세·빈 목록·마지막 페이지) 무한스크롤 대상이 아니다.
    if (!cards || !infinite) return;

    var sentinel = document.getElementById("sentinel");
    var spinner = document.getElementById("spinner");
    var button = document.getElementById("loadMoreBtn");
    var endMsg = document.getElementById("endMsg");

    // 현재까지 그려진 페이지 / 전체 페이지 수 / 활성 필터(angle)를 data-* 에서 읽는다.
    var currentPage = parseInt(cards.dataset.page, 10) || 1;
    var totalPages = parseInt(cards.dataset.totalPages, 10) || 1;
    var angle = cards.dataset.angle || "";

    var loading = false; // 동시 다중 요청 방지 플래그
    var observer = null;

    /**
     * 다음 페이지 카드 조각을 받아 그리드 끝에 append 한다.
     * 마지막 페이지에 도달하면 옵저버를 해제하고 종료 UI 로 전환한다.
     * @returns {Promise<void>}
     */
    function loadNext() {
      if (loading || currentPage >= totalPages) return;
      loading = true;
      showLoading(true);

      var nextPage = currentPage + 1;
      var url = "/blog/cards?page=" + nextPage;
      if (angle) url += "&angle=" + encodeURIComponent(angle);

      fetch(url, { headers: { "X-Requested-With": "fetch" } })
        .then(function (res) {
          if (!res.ok) throw new Error("HTTP " + res.status);
          return res.text();
        })
        .then(function (html) {
          // 받은 카드 조각을 그리드(grid) 끝에 그대로 삽입. 로더는 #cards 의 형제라 영향 없음.
          cards.insertAdjacentHTML("beforeend", html);
          // 방금 추가된 조각 안의 광고 유닛을 초기화(SSR 광고는 data-ad-pushed 로 건너뜀).
          initAds(cards);
          currentPage = nextPage;
          cards.dataset.page = String(currentPage);

          if (currentPage >= totalPages) {
            finish(); // 더 없음 → 정리
          } else {
            showLoading(false); // 다음 로드를 위해 버튼 복귀
          }
        })
        .catch(function () {
          // 실패 시 자동 로드를 멈추고, 버튼으로 수동 재시도하도록 둔다.
          if (spinner) spinner.hidden = true;
          if (button) {
            button.hidden = false;
            button.textContent = "다시 시도";
          }
        })
        .then(function () {
          loading = false;
        });
    }

    /**
     * 로딩 중 표시 토글: 스피너 on/off + 중복 클릭 방지를 위해 버튼 숨김.
     * @param {boolean} on 로딩 중이면 true
     * @returns {void}
     */
    function showLoading(on) {
      if (spinner) spinner.hidden = !on;
      if (button) button.hidden = on;
    }

    /**
     * 마지막 페이지 도달 처리: 옵저버 해제, 로더 제거, 종료 메시지 노출(푸터 접근성 확보).
     * @returns {void}
     */
    function finish() {
      if (observer) observer.disconnect();
      infinite.hidden = true;
      if (endMsg) endMsg.hidden = false;
    }

    // '더 보기' 버튼: JS 환경에선 페이지 이동 대신 그 자리에서 로드(수동 트리거 겸 폴백).
    if (button) {
      button.addEventListener("click", function (e) {
        e.preventDefault();
        loadNext();
      });
    }

    // 자동 로드: sentinel 이 뷰포트 400px 이내로 들어오면 미리 다음 페이지를 당겨온다.
    if (sentinel && "IntersectionObserver" in window) {
      observer = new IntersectionObserver(
        function (entries) {
          if (entries[0].isIntersecting) loadNext();
        },
        { rootMargin: "400px 0px" }
      );
      observer.observe(sentinel);
    }
    // IntersectionObserver 미지원 브라우저는 '더 보기' 버튼이 그대로 폴백 역할을 한다.
  }

  // defer 로 로드되지만 안전하게 DOM 준비 여부를 한 번 더 확인.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
