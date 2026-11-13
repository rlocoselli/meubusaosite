/* Location is kept in this tab only and expires after five minutes. */
(()=>{
 const key='meubusao-location-session-v1',lifetime=300000;let pending;
 function current(){try{const value=JSON.parse(sessionStorage.getItem(key));if(value&&Date.now()-value.at>=0&&Date.now()-value.at<lifetime&&Number.isFinite(value.coords.latitude)&&Number.isFinite(value.coords.longitude)&&Math.abs(value.coords.latitude)<=90&&Math.abs(value.coords.longitude)<=180)return value;sessionStorage.removeItem(key)}catch{}return null}
 function get({refresh=false}={}){const cached=!refresh&&current();if(cached)return Promise.resolve(cached);if(pending)return pending;if(!window.isSecureContext)return Promise.reject({code:'insecure'});if(!navigator.geolocation)return Promise.reject({code:'unsupported'});
  pending=new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(position=>{const value={coords:{latitude:position.coords.latitude,longitude:position.coords.longitude,accuracy:position.coords.accuracy},at:Date.now()};try{sessionStorage.setItem(key,JSON.stringify(value))}catch{}resolve(value)},reject,{enableHighAccuracy:true,timeout:15000,maximumAge:60000})).finally(()=>{pending=null});return pending
 }
 function errorKey(error){return error.code===1?'geo_denied':error.code===3?'geo_timeout':error.code==='insecure'?'geo_insecure':'geo_unavailable'}
 window.MeubusaoLocation={current,get,errorKey};
})();
