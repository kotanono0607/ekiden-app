const CACHE_NAME = 'ekiden-app-v1';
const STATIC_CACHE = 'ekiden-static-v1';

// 静的ファイルのキャッシュリスト
const STATIC_ASSETS = [
    '/',
    '/static/manifest.json',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'
];

// インストール時にキャッシュ
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// 古いキャッシュを削除
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name !== CACHE_NAME && name !== STATIC_CACHE)
                    .map(name => caches.delete(name))
            );
        }).then(() => self.clients.claim())
    );
});

// リクエストの処理
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // POSTリクエストはキャッシュしない
    if (request.method !== 'GET') {
        return;
    }

    // APIリクエストはネットワーク優先
    if (url.pathname.includes('/api/') ||
        url.pathname.includes('/export/') ||
        url.pathname.includes('/add') ||
        url.pathname.includes('/edit') ||
        url.pathname.includes('/delete')) {
        event.respondWith(networkFirst(request));
        return;
    }

    // 静的ファイルはキャッシュ優先
    if (url.pathname.startsWith('/static/') ||
        url.hostname.includes('cdn.jsdelivr.net')) {
        event.respondWith(cacheFirst(request));
        return;
    }

    // その他はネットワーク優先（オフライン時はキャッシュ）
    event.respondWith(networkFirst(request));
});

// キャッシュ優先戦略
async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) {
        return cached;
    }
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        return new Response('Offline', { status: 503, statusText: 'Offline' });
    }
}

// ネットワーク優先戦略
async function networkFirst(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        const cached = await caches.match(request);
        if (cached) {
            return cached;
        }
        // オフラインページを返す
        return caches.match('/') || new Response(
            '<html><body><h1>オフラインです</h1><p>ネットワーク接続を確認してください。</p></body></html>',
            { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
        );
    }
}
