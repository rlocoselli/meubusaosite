const VERSION='meubusao-offline-v2';
const STATIC=VERSION+'-static',PAGES=VERSION+'-pages',DATA=VERSION+'-data';
const ASSETS=['/offline','/my-space','/static/css/app.css','/static/js/app.js','/static/js/transit.js','/static/js/travel.js','/static/vendor/leaflet/leaflet.js','/static/vendor/leaflet/leaflet.css','/static/vendor/leaflet/images/marker-icon.png','/static/vendor/leaflet/images/marker-shadow.png'];
self.addEventListener('install',event=>event.waitUntil(caches.open(STATIC).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('meubusao-offline-')&&!key.startsWith(VERSION+'-')).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
async function stored(response){const headers=new Headers(response.headers);headers.set('X-Saved-At',new Date().toISOString());return new Response(await response.clone().arrayBuffer(),{status:response.status,statusText:response.statusText,headers})}
async function trim(cache,max){const keys=await cache.keys();await Promise.all(keys.slice(0,Math.max(0,keys.length-max)).map(key=>cache.delete(key)))}
function volatile(url){return /\/vehicles$|\/nearby$|\/alerts$/.test(url.pathname)}
async function fallback(request,cache){const cached=await cache.match(request)||await caches.match(request);if(!cached)throw Error('uncached');const headers=new Headers(cached.headers);headers.set('X-Offline','true');if(request.mode==='navigate'){const html=await cached.text(),stamp=headers.get('X-Saved-At')||'';return new Response(html.replace('</body>',`<script>document.documentElement.dataset.offlineSaved=${JSON.stringify(stamp)};</script></body>`),{status:200,headers})}return new Response(await cached.arrayBuffer(),{status:cached.status,headers})}
self.addEventListener('fetch',event=>{
 const request=event.request,url=new URL(request.url);if(request.method!=='GET'||url.origin!==self.location.origin||url.pathname==='/sw.js'||volatile(url)||url.pathname.startsWith('/lang/'))return;
 const navigation=request.mode==='navigate',api=url.pathname.startsWith('/api/'),asset=url.pathname.startsWith('/static/');if(!navigation&&!api&&!asset)return;
 event.respondWith((async()=>{
  const cache=await caches.open(navigation?PAGES:api?DATA:STATIC);
  if(asset){const existing=await cache.match(request);if(existing)return existing}
  try{
   const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),navigation?5000:15000);
   let response;
   try{response=await fetch(request,{signal:controller.signal})}finally{clearTimeout(timer)}
   if(response.ok){
    let eligible=true;
    if(api){const payload=await response.clone().json();eligible=payload.connected!==false}
    if(eligible){try{await cache.put(request,await stored(response));await trim(cache,navigation?25:80)}catch(error){/* Keep online pages usable if storage is full. */}}
   }
   return response;
  }catch(error){
   try{return await fallback(request,cache)}catch(missing){
    if(navigation){const offline=await caches.match('/offline');if(offline)return offline}
    return new Response(JSON.stringify({connected:false,items:[],offline:true}),{status:503,headers:{'Content-Type':'application/json'}});
   }
  }
 })());
});
self.addEventListener('message',event=>{if(event.data?.type==='clear-offline')event.waitUntil(Promise.all([caches.delete(PAGES),caches.delete(DATA)]).then(()=>event.source?.postMessage({type:'offline-cleared'})))});
self.addEventListener('notificationclick',event=>{event.notification.close();const url=event.notification.data?.url;let target='/my-space';try{const parsed=new URL(url,self.location.origin);if(parsed.origin===self.location.origin)target=parsed.href}catch(error){}event.waitUntil(self.clients.matchAll({type:'window'}).then(async clients=>{const existing=clients.find(client=>client.url===target);if(existing)return existing.focus();return self.clients.openWindow(target)}))});
