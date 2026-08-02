function parseData(id){try{return JSON.parse(document.getElementById(id)?.textContent||'[]')}catch(e){return[]}}
function coords(row){const lat=Number(row.stop_lat??row.stopLat??row.lat??row.shape_pt_lat);const lon=Number(row.stop_lon??row.stopLon??row.lon??row.lng??row.shape_pt_lon);return Number.isFinite(lat)&&Number.isFinite(lon)?[lat,lon]:null}
function tile(map){L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap',maxZoom:19}).addTo(map)}
function initCityMap(lat,lon,name){const el=document.getElementById('cityMap');if(!el)return;const map=L.map(el,{zoomControl:false}).setView([lat,lon],12);tile(map);L.control.zoom({position:'bottomright'}).addTo(map);const points=[];parseData('stopsData').forEach(s=>{const c=coords(s);if(!c)return;points.push(c);const marker=L.circleMarker(c,{radius:5,color:'#fff',weight:2,fillColor:'#0c7662',fillOpacity:.92}).addTo(map);marker.on('click',()=>openStopSheet(s,c));marker.on('mouseover',()=>marker.setStyle({radius:7,fillColor:'#d9ff43',color:'#071b2b'}));marker.on('mouseout',()=>marker.setStyle({radius:5,fillColor:'#0c7662',color:'#fff'}))});if(points.length)map.fitBounds(points,{padding:[35,35],maxZoom:14});else L.marker([lat,lon]).bindPopup(name).addTo(map)}
function initLineMap(lat,lon,color){const el=document.getElementById('lineMap');if(!el)return;const map=L.map(el).setView([lat,lon],12);tile(map);let shape=parseData('shapeData').map(coords).filter(Boolean);let stops=parseData('lineStops');let located=stops.map(s=>({stop:s,point:coords(s)})).filter(x=>x.point);if(shape.length)L.polyline(shape,{color,weight:6,opacity:.9}).addTo(map);located.forEach(x=>L.circleMarker(x.point,{radius:6,color,weight:4,fillColor:'#fff',fillOpacity:1}).bindPopup(x.stop.stop_name||x.stop.stopName||'Stop').addTo(map));const all=shape.length?shape:located.map(x=>x.point);if(all.length)map.fitBounds(all,{padding:[40,40]})}
document.getElementById('routeSearch')?.addEventListener('input',e=>{const q=e.target.value.toLowerCase();document.querySelectorAll('.route-row').forEach(r=>r.hidden=!r.dataset.search.includes(q))});
document.getElementById('departuresForm')?.addEventListener('submit',async e=>{e.preventDefault();const form=e.currentTarget,out=document.getElementById('departureResults'),data=new FormData(form);out.innerHTML='<div class="empty">•••</div>';try{const qs=new URLSearchParams(data);const res=await fetch(`/api/${form.dataset.city}/departures?${qs}`);const json=await res.json();out.innerHTML=(json.items||[]).map(d=>`<div class="departure-item"><span>${d.route_short_name||d.routeShortName||d.route_id||'Bus'}</span><b>${d.departure_time||d.departureTime||d.time||'—'}</b><span>${d.trip_headsign||d.headsign||d.stop_name||''}</span></div>`).join('')||'<div class="empty">No departures found</div>'}catch(err){out.innerHTML='<div class="empty">Service temporarily unavailable</div>'}});

const consentKey='meubusao-consent-v1';
const cookieBanner=document.getElementById('cookieBanner');
const cookieOptions=document.getElementById('cookieOptions');
const cookieSave=document.getElementById('cookieSave');
const cookieCustomize=document.getElementById('cookieCustomize');
function saveConsent(optional){localStorage.setItem(consentKey,JSON.stringify({essential:true,optional,updated:new Date().toISOString()}));cookieBanner.hidden=true;document.documentElement.dataset.externalConsent=optional?'granted':'denied'}
function openCookieSettings(){cookieBanner.hidden=false;cookieOptions.hidden=false;cookieSave.hidden=false;cookieCustomize.hidden=true;const saved=JSON.parse(localStorage.getItem(consentKey)||'{}');document.getElementById('optionalCookies').checked=Boolean(saved.optional)}
try{const saved=JSON.parse(localStorage.getItem(consentKey)||'null');if(!saved)cookieBanner.hidden=false;else document.documentElement.dataset.externalConsent=saved.optional?'granted':'denied'}catch(e){cookieBanner.hidden=false}
document.querySelectorAll('[data-consent]').forEach(button=>button.addEventListener('click',()=>saveConsent(button.dataset.consent==='all')));
cookieCustomize?.addEventListener('click',openCookieSettings);
cookieSave?.addEventListener('click',()=>saveConsent(document.getElementById('optionalCookies').checked));
document.querySelectorAll('[data-cookie-settings]').forEach(button=>button.addEventListener('click',openCookieSettings));

const stopSheet=document.getElementById('stopSheet');
let selectedStop=null;
function closeStopSheet(){if(!stopSheet)return;stopSheet.classList.remove('open');stopSheet.setAttribute('aria-hidden','true');document.getElementById('sheetBackdrop')?.classList.remove('open')}
function emptySheet(container){container.innerHTML=`<p class="sheet-empty">${stopSheet.dataset.empty}</p>`}
async function openStopSheet(stop,point){
 if(!stopSheet)return;selectedStop={stop,point};
 const stopId=String(stop.stop_id??stop.stopId??stop.id??'');
 document.getElementById('stopSheetName').textContent=stop.stop_name||stop.stopName||stop.name||stopId;
 document.getElementById('stopSheetCode').textContent=stopId;
 document.getElementById('stopSheetLoading').hidden=false;document.getElementById('stopSheetContent').hidden=true;
 stopSheet.classList.add('open');stopSheet.setAttribute('aria-hidden','false');document.getElementById('sheetBackdrop')?.classList.add('open');
 try{
  const response=await fetch(`/api/${stopSheet.dataset.city}/stop/${encodeURIComponent(stopId)}`);const data=await response.json();
  const routes=document.getElementById('stopSheetRoutes'),departures=document.getElementById('stopSheetDepartures');
  routes.innerHTML=(data.routes||[]).map(route=>`<a href="/city/${stopSheet.dataset.city}/line/${encodeURIComponent(route.id)}" class="sheet-route"><b style="background:${route.color};color:${route.text_color}">${route.short}</b><span>${route.name||route.short}</span></a>`).join('');if(!routes.innerHTML)emptySheet(routes);
  departures.innerHTML=(data.departures||[]).map(item=>`<div class="sheet-departure"><b style="background:#${String(item.route_color||'0c7662').replace('#','')}">${item.route_short_name||item.route_id||'•'}</b><span><strong>${item.trip_headsign||item.route_long_name||''}</strong><small>${stopSheet.dataset.scheduled}</small></span><time>${item.departure_time||item.time||'—'}</time></div>`).join('');if(!departures.innerHTML)emptySheet(departures);
 }catch(error){emptySheet(document.getElementById('stopSheetRoutes'));emptySheet(document.getElementById('stopSheetDepartures'))}
 document.getElementById('stopSheetLoading').hidden=true;document.getElementById('stopSheetContent').hidden=false;
}
document.getElementById('stopSheetClose')?.addEventListener('click',closeStopSheet);document.getElementById('sheetBackdrop')?.addEventListener('click',closeStopSheet);document.addEventListener('keydown',e=>{if(e.key==='Escape')closeStopSheet()});
document.getElementById('stopDirections')?.addEventListener('click',()=>{if(!selectedStop)return;const [lat,lon]=selectedStop.point;const destination=`${lat},${lon}`;const openRoute=origin=>window.open(`https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}&travelmode=transit`,'_blank','noopener');if(!navigator.geolocation){openRoute('');return}navigator.geolocation.getCurrentPosition(position=>openRoute(`${position.coords.latitude},${position.coords.longitude}`),()=>{alert(stopSheet.dataset.locationError);openRoute('')},{enableHighAccuracy:false,timeout:7000,maximumAge:300000})});
