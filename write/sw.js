// 최소 서비스워커 — 설치가능성(홈화면 추가) + 입력폼 셸 오프라인 캐시.
// POST(/api/journal)는 절대 캐시/가로채지 않음(항상 네트워크).
const CACHE = 'woohoo-journal-write-v1';
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
  // 셸은 cache-first, 그 외 네트워크 우선
  e.respondWith(caches.match(request).then((hit) => hit || fetch(request)));
});
