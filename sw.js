// Natura Fenua – fonctionne hors ligne. Change le numéro à chaque nouvelle version.
const CACHE='natura-fenua-0.4.6';
const FILES=['./','index.html','manifest.json','data.json','icon-192.png','icon-512.png','vendor/leaflet/leaflet.js','vendor/leaflet/leaflet.css','vendor/tahiti.geojson','demo/nono.jpg'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(FILES)));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(n=>n!==CACHE).map(n=>caches.delete(n)))));self.clients.claim()});
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=='GET'||u.pathname.endsWith('version.json'))return;
  // Fiches et empreintes : réseau d'abord (pour avoir les nouveautés), sinon la copie gardée.
  if(u.origin===location.origin&&(u.pathname.includes('/refs/')||u.pathname.endsWith('data.json'))){
    e.respondWith(fetch(e.request).then(r=>{const c=r.clone();caches.open(CACHE).then(x=>x.put(e.request,c));return r}).catch(()=>caches.match(e.request)));return}
  // Le reste (app, IA téléchargée une fois) : copie gardée d'abord.
  if(u.origin===location.origin||u.host==='cdn.jsdelivr.net'||u.host==='storage.googleapis.com'||u.host==='tile.openstreetmap.org'){
    e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).then(res=>{if(res.ok){const c=res.clone();caches.open(CACHE).then(x=>x.put(e.request,c))}return res})))}
});
