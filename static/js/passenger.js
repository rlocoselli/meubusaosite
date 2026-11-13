/* Passenger navigation and welcome-page tools layered over the transit app. */
(()=>{
 'use strict';
 const ux=JSON.parse(document.getElementById('uxCopy')?.textContent||'{}'),cities=JSON.parse(document.getElementById('citiesData')?.textContent||'{}');
 const t=key=>ux[key]||key,$=id=>document.getElementById(id),node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e};
 const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}};
 const write=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value))}catch{}};
 const cityPath=id=>`/city/${encodeURIComponent(id)}`;
 const city=location.pathname.match(/^\/city\/([^/]+)/)?.[1],remembered=read('meubusao-city','');
 if(city&&cities[city])write('meubusao-city',city);
 const menu=$('mainNav');function setMenu(open){menu?.classList.toggle('mobile-open',open);$('menuToggle')?.setAttribute('aria-expanded',String(open));if(open)menu?.querySelector('a')?.focus()}
 $('menuToggle')?.addEventListener('click',()=>setMenu(!menu.classList.contains('mobile-open')));
 $('bottomMore')?.addEventListener('click',()=>{setMenu(!menu.classList.contains('mobile-open'));const d=menu?.querySelector('details');if(d)d.open=true});
 document.addEventListener('keydown',e=>{if(e.key==='Escape')setMenu(false)});
 const homeCity=$('homeCity');if(homeCity&&cities[remembered])homeCity.value=remembered;
 $('transportSearch')?.addEventListener('submit',e=>{e.preventDefault();const f=e.currentTarget;if(!f.reportValidity())return;write('meubusao-city',homeCity.value);location.href=`${cityPath(homeCity.value)}?q=${encodeURIComponent(f.elements.q.value)}`});
 const geo=()=>new Promise((resolve,reject)=>navigator.geolocation?navigator.geolocation.getCurrentPosition(resolve,reject,{timeout:10000,maximumAge:60000}):reject());
 function distance(a,b){const r=Math.PI/180,x=Math.sin((b[0]-a[0])*r/2)**2+Math.cos(a[0]*r)*Math.cos(b[0]*r)*Math.sin((b[1]-a[1])*r/2)**2;return 6371000*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x))}
 async function nearby(){const status=$('homeStatus');status.textContent=t('loading');try{const p=await geo();const nearest=Object.entries(cities).map(([id,c])=>({id,d:distance([p.coords.latitude,p.coords.longitude],[c.lat,c.lon])})).sort((a,b)=>a.d-b.d)[0];if(!nearest||nearest.d>100000){status.textContent=t('outside_city');return}location.href=`${cityPath(nearest.id)}?nearby=1`}catch{status.textContent=t('location_denied')}}
 $('homeNearby')?.addEventListener('click',nearby);
 document.querySelectorAll('[data-nearby-link]').forEach(a=>{if(city||cities[remembered])a.href=`${cityPath(city||remembered)}?nearby=1`;else if($('homeNearby'))a.onclick=e=>{e.preventDefault();nearby()}});
 // Preserve saved stops created before the upstream unified favorites format.
 const oldStops=read('meubusao-stops-v1',[]);if(Array.isArray(oldStops)&&oldStops.length){const all=getFavorites();for(const item of oldStops){const value={...item,type:'stop',short:'⌖',color:'#0c7662',textColor:'#fff'};if(!all.some(x=>favoriteKey(x)===favoriteKey(value)))all.push(value)}saveFavorites(all);write('meubusao-stops-v1',[])}
 function homeSaved(){if(!$('homeSaved'))return;const items=getFavorites().slice(0,6);$('homeSaved').replaceChildren(...items.map(x=>{const a=node('a',`${x.type==='stop'?'⌖':x.short||'•'} · ${x.name||x.id} · ${x.cityName||x.city}`,'saved-link');a.href=`${cityPath(x.city)}/${x.type==='stop'?'stop':'line'}/${encodeURIComponent(x.id)}`;return a}));$('homeSavedSection').hidden=!items.length}
 homeSaved();window.addEventListener('favoriteschanged',homeSaved);window.addEventListener('storage',homeSaved);
 // Local Leaflet stays bundled. Map tiles and viewport requests start on demand.
 let mapConfig,started=false;
 const originalCity=window.initCityMap,originalLine=window.initLineMap;
 window.initCityMap=(...args)=>{mapConfig={kind:'city',args}};
 window.initLineMap=(...args)=>{mapConfig={kind:'line',args}};
 function ensureMap(){if(started||!mapConfig)return;started=true;if(mapConfig.kind==='city')originalCity(...mapConfig.args);else originalLine(...mapConfig.args);$('passengerMapLoad')?.setAttribute('hidden','');}
 const network=document.querySelector('.network-layout,.line-layout');
 if(network){
  const list=network.querySelector('.route-panel,.stop-card'),mapPanel=network.querySelector('.map-wrap');
  const controls=node('div',undefined,'passenger-view-controls'),tabs=node('div',undefined,'view-tabs');
  const listButton=node('button',t('list')),mapButton=node('button',t('map'));for(const b of [listButton,mapButton])b.type='button';
  listButton.setAttribute('aria-pressed','true');mapButton.setAttribute('aria-pressed','false');tabs.append(listButton,mapButton);controls.append(tabs);network.before(controls);network.classList.add('passenger-network');
  function view(showMap){list.hidden=showMap;mapPanel.hidden=!showMap;listButton.setAttribute('aria-pressed',String(!showMap));mapButton.setAttribute('aria-pressed',String(showMap));if(showMap&&started)requestAnimationFrame(()=>{(window.transitCityMap||window.transitLineMap)?.invalidateSize()})}
  view(false);listButton.onclick=()=>view(false);mapButton.onclick=()=>view(true);
  const note=node('div',undefined,'passenger-map-notice');note.append(node('p',t('map_notice')));const load=node('button',t('load_map'),'btn dark');load.type='button';load.id='passengerMapLoad';load.onclick=()=>{ensureMap();note.hidden=true};note.append(load);mapPanel.prepend(note);
  document.querySelectorAll('[data-preview-route],[data-focus-stop]').forEach(b=>b.addEventListener('click',()=>{view(true);ensureMap();note.hidden=true},true));
  if($('routeSearch')){
   const routeList=$('routeList'),stopList=node('div',undefined,'passenger-stop-results');stopList.hidden=true;routeList.after(stopList);
   const routes=node('button',t('lines')),stops=node('button',t('stops')),kinds=node('div',undefined,'content-tabs');routes.type=stops.type='button';routes.setAttribute('aria-pressed','true');stops.setAttribute('aria-pressed','false');kinds.append(routes,stops);routeList.before(kinds);
   const modes=node('select');modes.setAttribute('aria-label',t('all_modes'));for(const [value,label] of [['','all_modes'],['3','bus'],['0','tram'],['1','metro'],['2','rail'],['4','ferry']]){if(value&&!document.querySelector(`.route-row[data-mode="${value}"]`))continue;const option=node('option',t(label));option.value=value;modes.append(option)}kinds.before(modes);modes.className='passenger-mode-filter';
   let kind='routes',timer,request;function filter(){const q=normalizeSearch($('routeSearch').value);document.querySelectorAll('.route-row').forEach(row=>row.hidden=!normalizeSearch(row.dataset.search).includes(q)||Boolean(modes.value&&row.dataset.mode!==modes.value));if(kind!=='stops')return;clearTimeout(timer);request?.abort();stopList.replaceChildren(node('p',t('loading')));timer=setTimeout(async()=>{request=new AbortController();try{const r=await fetch(`/api/${encodeURIComponent(city)}/stops?${new URLSearchParams({q:$('routeSearch').value})}`,{signal:request.signal});if(!r.ok)throw Error();const data=await r.json();stopList.replaceChildren(...data.items.map(stop=>{const a=node('a',`${stop.name} · ${stop.id}`,'stop-row');a.href=`${cityPath(city)}/stop/${encodeURIComponent(stop.id)}`;return a}));if(!data.items.length)stopList.append(node('p',data.connected?t('no_matches'):t('unavailable')))}catch(e){if(e.name!=='AbortError')stopList.replaceChildren(node('p',t('unavailable')))}},180)}
   function choose(value){kind=value;routeList.hidden=value!=='routes';stopList.hidden=value!=='stops';modes.hidden=value!=='routes';routes.setAttribute('aria-pressed',String(value==='routes'));stops.setAttribute('aria-pressed',String(value==='stops'));filter()}
   routes.onclick=()=>choose('routes');stops.onclick=()=>choose('stops');modes.onchange=filter;$('routeSearch').addEventListener('input',filter);
   const q=new URLSearchParams(location.search).get('q');if(q){$('routeSearch').value=q;filter();if(![...routeList.querySelectorAll('.route-row')].some(x=>!x.hidden))choose('stops');controls.scrollIntoView()}
  }
 }
 const params=new URLSearchParams(location.search);if(params.has('nearby')&&$('findNearby')){$('findNearby').scrollIntoView();$('findNearby').click()}
 const suggestion=document.querySelector('.suggestion-section textarea');if(suggestion&&params.has('stop'))suggestion.value=`${params.get('city')||''} · ${params.get('stop')}\n\n`;
 const sheet=$('stopSheet');if(sheet){let previous;const originalOpen=window.openStopSheet,originalClose=window.closeStopSheet;window.openStopSheet=async(...args)=>{previous=document.activeElement;document.body.classList.add('sheet-open');sheet.setAttribute('role','dialog');sheet.setAttribute('aria-modal','true');const result=originalOpen(...args);$('stopSheetClose').focus();return result};window.closeStopSheet=()=>{originalClose();document.body.classList.remove('sheet-open');previous?.focus()};for(const id of ['stopSheetClose','sheetBackdrop'])$(id)?.addEventListener('click',()=>{document.body.classList.remove('sheet-open');previous?.focus()});const report=node('a',t('report'),'btn');report.href='/contacts.html#suggestions';sheet.querySelector('.sheet-tools')?.append(report);sheet.addEventListener('keydown',e=>{if(e.key!=='Tab')return;const elements=[...sheet.querySelectorAll('button,a[href],input')].filter(x=>!x.disabled&&x.getClientRects().length);if(e.shiftKey&&document.activeElement===elements[0]){e.preventDefault();elements.at(-1)?.focus()}else if(!e.shiftKey&&document.activeElement===elements.at(-1)){e.preventDefault();elements[0]?.focus()}})}
 // The upstream stop page remains the shareable, full-day timetable.
 const stopHeading=document.querySelector('.stop-head');if(stopHeading){const report=node('a',t('report'),'btn');report.href=`/contacts.html?city=${encodeURIComponent(city)}&stop=${encodeURIComponent(location.pathname.split('/stop/')[1]||'')}#suggestions`;stopHeading.append(report)}
 document.querySelectorAll('[data-local-time]').forEach(e=>{const date=new Date(e.dataset.localTime);if(!Number.isNaN(date.valueOf()))e.textContent=date.toLocaleString(document.documentElement.lang)});
})();
