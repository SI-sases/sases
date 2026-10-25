// static/service-worker.js
const CACHE_NAME = 'sases-cache-v61';
const STATIC_ASSETS = [
  '/static/index.html',
  '/static/favicon.svg',
  '/static/modules/main.js',
  '/static/modules/api.js',
  '/static/modules/auth.js',
  '/static/modules/messages.js',
  '/static/modules/chat.js',
  '/static/modules/contacts.js',
  '/static/modules/discover.js',
  '/static/modules/me.js',
  '/static/modules/utils.js'
];

// 安装：预缓存静态资源
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// 激活：清理旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// 请求拦截：只处理 http/https 请求，静态资源缓存优先，API 网络优先
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // 忽略非 http/https 协议（如 chrome-extension://）
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    return;
  }

  // 跳过跨域请求（unpkg / cdn 等），交给浏览器直接处理
  if (url.origin !== location.origin) {
    return;
  }

  // 不缓存 API 请求
  if (
    url.pathname.startsWith('/token') ||
    url.pathname.startsWith('/agent') ||
    url.pathname.startsWith('/messages') ||
    url.pathname.startsWith('/models') ||
    url.pathname.startsWith('/credits') ||
    url.pathname.startsWith('/knowledge') ||
    url.pathname.startsWith('/stats') ||
    url.pathname.startsWith('/auth') ||
    url.pathname.startsWith('/api') ||
    url.pathname.startsWith('/seeds')
  ) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(event.request).then((response) => {
        // 只缓存成功的 GET 请求
        if (response.status === 200 && event.request.method === 'GET') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});