// 최소 서비스워커 — 설치가능성(홈화면 추가) + 입력폼 셸 오프라인 캐시.
// POST(/api/journal)는 절대 캐시/가로채지 않음(항상 네트워크).
const CACHE = 'woohoo-journal-write-v2';
const SHELL = ['./', './index.html', './app.js', './manifest.webmanifest'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const { request } = e;
  if (request.method !== 'GET') return;            // POST 등은 통과(네트워크)
  const url = new URL(request.url);
  if (url.pathname.startsWith('/api/')) return;     // API 는 캐시 안 함
  // 네트워크 우선(새 app.js 즉시 반영), 오프라인일 때만 캐시된 셸 사용
  e.respondWith(
    fetch(request)
      .then((res) => {
        if (res.ok && url.origin === self.location.origin) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(request, copy));
        }
        return res;
      })
      .catch(() => caches.match(request))
  );
});
