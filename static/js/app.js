function parseData(id){try{return JSON.parse(document.getElementById(id)?.textContent||'[]')}catch(e){return[]}}
function coords(row){const a=row.stop_lat??row.stopLat??row.lat??row.latitude??row.shape_pt_lat??row.shapePtLat;const b=row.stop_lon??row.stopLon??row.lon??row.lng??row.longitude??row.shape_pt_lon??row.shapePtLon;if(a==null||b==null||a===''||b==='')return null;const lat=Number(a),lon=Number(b);return Number.isFinite(lat)&&Number.isFinite(lon)&&Math.abs(lat)<=90&&Math.abs(lon)<=180?[lat,lon]:null}
function tile(map){L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap',maxZoom:19}).addTo(map)}
function initCityMap(lat,lon,name){
 const el=document.getElementById('cityMap');if(!el)return;const map=L.map(el,{zoomControl:false,preferCanvas:true}).setView([lat,lon],12);window.transitCityMap=map;tile(map);L.control.zoom({position:'bottomright'}).addTo(map);const layer=L.layerGroup().addTo(map);let request,generation=0,timer;
 async function load(){request?.abort();request=new AbortController();const signal=request.signal,current=++generation,bounds=map.getBounds();const box=[Math.max(-90,bounds.getSouth()),Math.max(-180,Math.min(180,bounds.getWest())),Math.min(90,bounds.getNorth()),Math.min(180,Math.max(-180,bounds.getEast()))];try{const data=await getTransit(`/api/${encodeURIComponent(el.dataset.city)}/map-stops?${new URLSearchParams({bounds:box.join(','),zoom:map.getZoom()})}`,signal);if(current!==generation)return;layer.clearLayers();for(let index=0;index<data.items.length;index++){if(current!==generation)return;const stop=data.items[index],point=coords(stop);if(!point)continue;if(stop.count>1){const marker=L.marker(point,{icon:L.divIcon({className:'stop-cluster',html:`<span>${Number(stop.count)}</span>`,iconSize:[40,40],iconAnchor:[20,20]})}).addTo(layer);marker.bindTooltip(element('span','',travelCopy.cluster_hint));marker.on('click',()=>{if(map.getZoom()<18){map.fitBounds(stop.bounds,{maxZoom:map.getZoom()+3,padding:[30,30]});return}const popup=element('div','cluster-stops');(stop.members||[]).forEach(member=>{const button=element('button','',member.name);button.type='button';button.addEventListener('click',()=>openStopSheet(member,coords(member)));popup.append(button)});marker.bindPopup(popup).openPopup()})}else{const marker=L.circleMarker(point,{radius:5,color:'#fff',weight:2,fillColor:'#0c7662',fillOpacity:.92}).addTo(layer);marker.bindTooltip(element('span','',stop.name));marker.on('click',()=>openStopSheet(stop,point))}if(index%100===99)await new Promise(resolve=>requestAnimationFrame(resolve))}}catch(error){if(error.name!=='AbortError')toast(transitCopy.unavailable)}}
 map.on('moveend',()=>{clearTimeout(timer);timer=setTimeout(load,200)});load();startVehicles(map,document.querySelector('[data-vehicles-city]'));
}

function initLineMap(lat,lon,color){
 const el=document.getElementById('lineMap');if(!el)return;const map=L.map(el).setView([lat,lon],12);tile(map);startVehicles(map,document.querySelector('[data-vehicles-city]'));
 const shape=parseData('shapeData').sort((a,b)=>Number(a.shape_pt_sequence??a.shapePtSequence??0)-Number(b.shape_pt_sequence??b.shapePtSequence??0)).map(coords).filter(Boolean);
 const located=parseData('lineStops').map((stop,index)=>({stop,index,point:coords(stop)})).filter(x=>x.point);
 const exact=shape.length>1,path=exact?shape:located.map(x=>x.point),markers=new Map();
 document.getElementById('routeGeometryLabel').textContent=path.length>1?(exact?el.dataset.exact:el.dataset.approximate):el.dataset.timetable;
 if(path.length>1){L.polyline(path,{color:'#fff',weight:10,opacity:.9}).addTo(map);L.polyline(path,{color,weight:6,opacity:.95,dashArray:exact?null:'8 10'}).addTo(map)}
 located.forEach(({stop,index,point})=>{
  const marker=L.marker(point,{icon:L.divIcon({className:'numbered-stop',html:`<span style="border-color:${color}">${index+1}</span>`,iconSize:[28,28],iconAnchor:[14,14]})}).addTo(map);
  const popup=document.createElement('div'),name=document.createElement('strong'),link=document.createElement('a');name.textContent=stop.stop_name||stop.stopName||stop.name||String(index+1);link.textContent=el.dataset.timetable+' ↗';link.href=`/city/${encodeURIComponent(el.dataset.city)}/stop/${encodeURIComponent(stop.stop_id??stop.stopId??stop.id??'')}`;popup.append(name,document.createElement('br'),link);marker.bindPopup(popup);markers.set(index,marker);
  marker.on('click',()=>{document.querySelectorAll('[data-stop-index]').forEach(row=>row.classList.toggle('selected',Number(row.dataset.stopIndex)===index));const row=document.querySelector(`[data-stop-index="${index}"]`);if(row&&!row.hidden){const panel=row.closest('.stop-card');if(window.matchMedia('(max-width:900px)').matches){panel.classList.remove('collapsed');const toggle=document.getElementById('toggleStops');toggle?.setAttribute('aria-expanded','true');if(toggle)toggle.textContent=transitCopy.collapse_stops+' ⌄';panel.scrollTo({top:panel.scrollTop+row.getBoundingClientRect().top-panel.getBoundingClientRect().top-25,behavior:'smooth'})}else row.scrollIntoView({behavior:'smooth',block:'nearest'})}});
 });
 const fit=()=>{const points=[...path,...located.map(x=>x.point)];if(points.length)map.fitBounds(points,{padding:[45,45],maxZoom:16})};fit();document.getElementById('fitRoute')?.addEventListener('click',fit);
 document.querySelectorAll('[data-focus-stop]').forEach(button=>{const marker=markers.get(Number(button.dataset.focusStop));button.disabled=!marker;button.addEventListener('click',()=>{document.querySelectorAll('[data-stop-index]').forEach(row=>row.classList.toggle('selected',row.dataset.stopIndex===button.dataset.focusStop));el.scrollIntoView({behavior:'smooth',block:'center'});map.setView(marker.getLatLng(),16);marker.openPopup()})});
}
const normalizeSearch=value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
document.getElementById('lineStopSearch')?.addEventListener('input',event=>{const query=normalizeSearch(event.target.value);document.querySelectorAll('[data-stop-index]').forEach(row=>row.hidden=!normalizeSearch(row.dataset.search).includes(query))});
const explorer=document.getElementById('cityExplorer');
if(explorer){let region='all',country='all';const cards=[...explorer.querySelectorAll('.city-card')];const update=()=>{const query=normalizeSearch(document.getElementById('citySearch').value);let count=0;cards.forEach(card=>{card.hidden=!((region==='all'||card.dataset.region===region)&&(country==='all'||card.dataset.country===country)&&normalizeSearch(card.dataset.search).includes(query));if(!card.hidden)count++});document.getElementById('cityCount').textContent=count;document.getElementById('cityEmpty').hidden=count>0;explorer.querySelectorAll('button[data-country]').forEach(button=>{button.hidden=button.dataset.country!=='all'&&!cards.some(card=>(region==='all'||card.dataset.region===region)&&card.dataset.country===button.dataset.country);const active=button.dataset.country===country;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active))})};explorer.querySelectorAll('button[data-region]').forEach(button=>button.addEventListener('click',()=>{region=button.dataset.region;country='all';explorer.querySelectorAll('button[data-region]').forEach(item=>{const active=item===button;item.classList.toggle('active',active);item.setAttribute('aria-pressed',String(active))});update()}));explorer.querySelectorAll('button[data-country]').forEach(button=>button.addEventListener('click',()=>{country=button.dataset.country;update()}));document.getElementById('citySearch').addEventListener('input',update)}

document.getElementById('routeSearch')?.addEventListener('input',e=>{const q=e.target.value.toLowerCase();document.querySelectorAll('.route-row').forEach(r=>r.hidden=!r.dataset.search.includes(q))});


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
 if(!stopSheet)return;
 selectedStop={stop,point};
 document.getElementById('stopDirections').disabled=!point;
 const stopId=String(stop.stop_id??stop.stopId??stop.id??'');
 const name=stop.stop_name||stop.stopName||stop.name||stopId;
 document.getElementById('stopSheetName').textContent=name;
 document.getElementById('stopSheetCode').textContent=stopId;
 document.getElementById('sheetAccessibility').textContent='♿ '+accessibilityText(String(stop.wheelchair??stop.wheelchair_boarding??'0'));
 const button=document.getElementById('sheetFavorite');button.dataset.favorite=JSON.stringify({type:'stop',id:stopId,city:stopSheet.dataset.city,cityName:document.querySelector('.city-hero h1')?.textContent,name,short:'⌖',color:'#0c7662',textColor:'#fff'});updateFavoriteButton(button);
 stopSheet.classList.add('open');stopSheet.setAttribute('aria-hidden','false');document.getElementById('sheetBackdrop')?.classList.add('open');
 await loadStopSheet();
}
document.getElementById('stopSheetClose')?.addEventListener('click',closeStopSheet);document.getElementById('sheetBackdrop')?.addEventListener('click',closeStopSheet);document.addEventListener('keydown',e=>{if(e.key==='Escape')closeStopSheet()});
document.getElementById('stopDirections')?.addEventListener('click',()=>{if(!selectedStop?.point)return;const [lat,lon]=selectedStop.point;const destination=`${lat},${lon}`;const openRoute=origin=>window.open(`https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}&travelmode=transit`,'_blank','noopener');if(!navigator.geolocation){openRoute('');return}navigator.geolocation.getCurrentPosition(position=>openRoute(`${position.coords.latitude},${position.coords.longitude}`),()=>{alert(stopSheet.dataset.locationError);openRoute('')},{enableHighAccuracy:false,timeout:7000,maximumAge:300000})});

const favoritesKey='meubusao-favorites-v1';
function getFavorites(){try{const value=JSON.parse(localStorage.getItem(favoritesKey)||'[]');return Array.isArray(value)?value:[]}catch(error){return[]}}
function favoriteKey(item){return `${item.type||'line'}::${item.city}::${item.id}`}
function saveFavorites(items){localStorage.setItem(favoritesKey,JSON.stringify(items));window.dispatchEvent(new CustomEvent('favoriteschanged'))}
function isFavorite(item){const key=favoriteKey(item);return getFavorites().some(saved=>favoriteKey(saved)===key)}
function updateFavoriteButton(button){const item=JSON.parse(button.dataset.favorite);const active=isFavorite(item);button.classList.toggle('active',active);button.firstChild.textContent=active?'★':'☆';button.setAttribute('aria-pressed',String(active))}
document.querySelectorAll('[data-favorite]').forEach(button=>{updateFavoriteButton(button);button.addEventListener('click',event=>{event.preventDefault();event.stopPropagation();const item=JSON.parse(button.dataset.favorite);let items=getFavorites();const key=favoriteKey(item);items=items.some(saved=>favoriteKey(saved)===key)?items.filter(saved=>favoriteKey(saved)!==key):[item,...items];saveFavorites(items);updateFavoriteButton(button)})});
function renderFavorites(){
 const lineGrid=document.getElementById('favoritesGrid'),stopGrid=document.getElementById('favoriteStopsGrid'),empty=document.getElementById('favoritesEmpty');if(!lineGrid||!empty)return;
 const items=getFavorites();lineGrid.replaceChildren();stopGrid?.replaceChildren();empty.hidden=items.length>0;
 items.forEach(item=>{const grid=item.type==='stop'?stopGrid:lineGrid;if(!grid)return;const card=document.createElement('article');card.className='favorite-card';const link=document.createElement('a');link.href=`/city/${encodeURIComponent(item.city)}/${item.type==='stop'?'stop':'line'}/${encodeURIComponent(item.id)}`;const badge=document.createElement('b');badge.textContent=item.short||'•';badge.style.background=item.color||'#2563eb';badge.style.color=item.textColor||'#fff';const copy=document.createElement('span');const title=document.createElement('strong');title.textContent=item.name||item.short;const city=document.createElement('small');city.textContent=item.cityName||item.city;copy.append(title,city);link.append(badge,copy);const remove=document.createElement('button');remove.type='button';remove.textContent='★';remove.title=grid.dataset.remove;remove.setAttribute('aria-label',grid.dataset.remove);remove.addEventListener('click',()=>{saveFavorites(getFavorites().filter(saved=>favoriteKey(saved)!==favoriteKey(item)));renderFavorites()});card.append(link,remove);grid.append(card)})
}
renderFavorites();window.addEventListener('favoriteschanged',()=>{renderFavorites();document.querySelectorAll('[data-favorite]').forEach(updateFavoriteButton)});window.addEventListener('storage',renderFavorites);
