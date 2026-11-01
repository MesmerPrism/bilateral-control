import {staticRequestAllowed} from './public-cache.mjs';
// Export sets the exact version and finite static shell. Local root never registers this worker.
const CACHE_VERSION='0ed0a17b7d27b60f8960922c926195ceb71c64d447f63931c3642773b069f664';
const STATIC_PATHS=["/bilateral-control/","/bilateral-control/app.mjs","/bilateral-control/bilateral-owner.mjs","/bilateral-control/capture-mode.mjs","/bilateral-control/decoder-policy.mjs","/bilateral-control/frame-status.mjs","/bilateral-control/gateway.mjs","/bilateral-control/hub.css","/bilateral-control/hub.mjs","/bilateral-control/icons/apple-touch-icon.png","/bilateral-control/icons/quest-multi-stream-192.png","/bilateral-control/icons/quest-multi-stream-512.png","/bilateral-control/index.html","/bilateral-control/live-owner.mjs","/bilateral-control/manifest.webmanifest","/bilateral-control/public-cache.mjs","/bilateral-control/pwa.mjs","/bilateral-control/session-view.mjs","/bilateral-control/style.css","/bilateral-control/view.mjs","/bilateral-control/viewer.html"];
const CACHE_PREFIX='questms-public-bilateral-v1-';
const CACHE_NAME=CACHE_PREFIX+CACHE_VERSION;
self.addEventListener('install',event=>event.waitUntil((async()=>{
 const cache=await caches.open(CACHE_NAME);
 // credentials omitted and redirects refused even for the public static shell.
 for(const path of STATIC_PATHS){const request=new Request(new URL(path,self.location.origin),{credentials:'omit',cache:'reload',redirect:'error',referrerPolicy:'no-referrer'});const response=await fetch(request);if(!response.ok||response.type!=='basic')throw Error('Static shell unavailable');await cache.put(request,response);}
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{
 for(const key of await caches.keys())if(key.startsWith(CACHE_PREFIX)&&key!==CACHE_NAME)await caches.delete(key);
})()));
self.addEventListener('fetch',event=>{
 if(!staticRequestAllowed(event.request,self.location.origin,STATIC_PATHS))return;
 event.respondWith((async()=>{
  const cache=await caches.open(CACHE_NAME),cached=await cache.match(event.request);
  return cached??fetch(event.request);
 })());
});
