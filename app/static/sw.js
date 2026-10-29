// Service Worker for Chara Survey Automation Android PWA
const CACHE_NAME = 'chara-survey-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/farmers',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  // Network first strategy
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
