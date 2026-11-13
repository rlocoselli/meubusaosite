(()=>{
 const key='meubusao-reading-v1';let settings;try{settings=JSON.parse(localStorage.getItem(key)||'{}')}catch{settings={}}if(!settings||typeof settings!=='object'||Array.isArray(settings))settings={}
 function apply(){document.documentElement.dataset.readingLarge=String(Boolean(settings.large));document.documentElement.dataset.readingContrast=String(Boolean(settings.contrast));document.querySelectorAll('[data-reading]').forEach(b=>b.setAttribute('aria-pressed',String(Boolean(settings[b.dataset.reading]))));try{localStorage.setItem(key,JSON.stringify(settings))}catch{}}
 document.querySelectorAll('[data-reading]').forEach(b=>b.onclick=()=>{settings[b.dataset.reading]=!settings[b.dataset.reading];apply()});document.querySelector('[data-reading-reset]')?.addEventListener('click',()=>{settings={};apply()});apply();
})();
