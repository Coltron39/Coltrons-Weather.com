/* ============================================================
   COLTRONS FIRST ALERT WEATHER - ONLINE NWS DATA ENGINE
   GitHub Pages version: no wx_feed.py and no local server needed.
   Data source: National Weather Service API
   ============================================================ */

const REFRESH_MS = 60000;
const PRIMARY = { name: "WISCONSIN RAPIDS", lat: 44.3836, lon: -89.8173 };
const CITY_POINTS = [
  ["SUPERIOR",46.7208,-92.1041],["ASHLAND",46.5927,-90.8838],
  ["EAU CLAIRE",44.8113,-91.4985],["LA CROSSE",43.8014,-91.2396],
  ["WAUSAU",44.9591,-89.6301],["RHINELANDER",45.6366,-89.4121],
  ["GREEN BAY",44.5133,-88.0133],["APPLETON",44.2619,-88.4154],
  ["SHEBOYGAN",43.7508,-87.7145],["MILWAUKEE",43.0389,-87.9065],
  ["KENOSHA",42.5847,-87.8212],["MADISON",43.0731,-89.4012],
  ["WISCONSIN RAPIDS",44.3836,-89.8173]
];

const ICONS = {
  clear:`<circle class="sun" cx="50" cy="50" r="19"/><g stroke="#ffcf3f" stroke-width="6" stroke-linecap="round"><line x1="50" y1="12" x2="50" y2="22"/><line x1="50" y1="78" x2="50" y2="88"/><line x1="12" y1="50" x2="22" y2="50"/><line x1="78" y1="50" x2="88" y2="50"/><line x1="24" y1="24" x2="31" y2="31"/><line x1="69" y1="69" x2="76" y2="76"/><line x1="24" y1="76" x2="31" y2="69"/><line x1="69" y1="31" x2="76" y2="24"/></g>`,
  clear_night:`<path class="moon" d="M62 20a32 32 0 1 0 20 45A34 34 0 0 1 62 20z"/><circle class="moon" cx="26" cy="26" r="2.5"/><circle class="moon" cx="80" cy="30" r="2"/>`,
  pcloudy:`<circle class="sun" cx="38" cy="36" r="15"/><g stroke="#ffcf3f" stroke-width="5" stroke-linecap="round"><line x1="38" y1="8" x2="38" y2="15"/><line x1="10" y1="36" x2="17" y2="36"/><line x1="18" y1="16" x2="23" y2="21"/><line x1="58" y1="16" x2="53" y2="21"/></g><path class="cloud" d="M38 78h34a15 15 0 0 0 1-30 21 21 0 0 0-39-5 14 14 0 0 0 4 35z"/>`,
  pcloudy_night:`<path class="moon" d="M52 18a24 24 0 1 0 15 34A26 26 0 0 1 52 18z"/><path class="cloud" d="M34 80h38a16 16 0 0 0 1-31 22 22 0 0 0-41-5 15 15 0 0 0 2 36z"/>`,
  cloudy:`<path class="cloud-dk" d="M30 52a19 19 0 0 1 35-9 16 16 0 0 1 3 30H32a13 13 0 0 1-2-21z"/><path class="cloud" d="M36 82h40a16 16 0 0 0 1-31 22 22 0 0 0-41-5 15 15 0 0 0 0 36z"/>`,
  rain:`<path class="cloud" d="M34 62h38a16 16 0 0 0 1-31 22 22 0 0 0-41-5 15 15 0 0 0 2 36z"/><g class="drop"><rect x="34" y="70" width="5" height="18" rx="2.5"/><rect x="52" y="74" width="5" height="18" rx="2.5"/><rect x="70" y="70" width="5" height="18" rx="2.5"/></g>`,
  storm:`<path class="cloud-dk" d="M32 60h38a16 16 0 0 0 1-31 22 22 0 0 0-41-5 15 15 0 0 0 2 36z"/><path class="bolt" d="M52 62 36 90h13l-4 18 22-30H53l6-16z"/>`,
  snow:`<path class="cloud" d="M34 60h38a16 16 0 0 0 1-31 22 22 0 0 0-41-5 15 15 0 0 0 2 36z"/><g class="flake" stroke-width="4" stroke-linecap="round"><line x1="38" y1="72" x2="38" y2="88"/><line x1="30" y1="80" x2="46" y2="80"/><line x1="66" y1="72" x2="66" y2="88"/><line x1="58" y1="80" x2="74" y2="80"/></g>`,
  fog:`<path class="cloud" d="M34 54h38a16 16 0 0 0 1-31 22 22 0 0 0-41-5 15 15 0 0 0 2 36z"/><g stroke="#cfe2f5" stroke-width="6" stroke-linecap="round"><line x1="24" y1="68" x2="80" y2="68"/><line x1="32" y1="82" x2="88" y2="82"/></g>`,
  wind:`<g stroke="#dff1ff" stroke-width="7" stroke-linecap="round" fill="none"><path d="M14 38h48a13 13 0 1 0-13-13"/><path d="M14 62h58a13 13 0 1 1-13 13"/><path d="M20 84h30"/></g>`
};

function icon(key,size){return `<svg class="wxicon" width="${size}" height="${size}" viewBox="0 0 100 100">${ICONS[key]||ICONS.pcloudy}</svg>`;}
const $=s=>document.querySelector(s);
const num=(v,d='--')=>(v===null||v===undefined||Number.isNaN(v)?d:v);
function tempClass(t){if(t==null)return'c-na';if(t>=95)return'c-extreme';if(t>=80)return'c-hot';if(t>=65)return'c-warm';if(t>=50)return'c-mild';if(t>=33)return'c-cool';if(t>=15)return'c-cold';return'c-frigid';}

function startClock(){
  const el=$('#clock'),dt=$('#date');
  const tick=()=>{const d=new Date(),h=d.getHours()%12||12,m=String(d.getMinutes()).padStart(2,'0'),ap=d.getHours()>=12?'PM':'AM';
    if(el)el.textContent=`${h}:${m} ${ap}`;
    if(dt)dt.textContent=d.toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'}).toUpperCase();};
  tick();setInterval(tick,1000);
}
function mountHeader(subtitle){
  const h=$('#header');if(!h)return;
  h.className='header';h.innerHTML=`<div class="logo-mark">C</div><div class="logo-text"><div class="l1">COLTRONS <em>FIRST ALERT</em> WEATHER</div><div class="l2">${subtitle||"WISCONSIN'S WEATHER AUTHORITY"}</div></div><div class="header-right"><div class="clock" id="clock">--:--</div><div class="date" id="date"></div></div>`;
  startClock();
}
function mountFooter(msg){
  const f=$('#footer');if(!f)return;
  f.className='footer';f.innerHTML=`<div class="brandchip">FIRST ALERT WX</div><div class="msg" id="footmsg">${msg||''}</div><div class="stamp" id="stamp">UPDATED --:--</div>`;
}
function rotate(el,items,ms=6000){if(!el||!items.length)return;let i=0;el.textContent=items[0];if(items.length===1)return;setInterval(()=>{i=(i+1)%items.length;el.style.opacity=0;setTimeout(()=>{el.textContent=items[i];el.style.opacity=1},260)},ms);}

async function api(url){
  const r=await fetch(url,{headers:{Accept:'application/geo+json, application/ld+json, application/json'},cache:'no-store'});
  if(!r.ok)throw new Error(`NWS ${r.status}`);
  return r.json();
}
const cToF=c=>c==null?null:Math.round(c*9/5+32);
const mpsToMph=v=>v==null?null:Math.round(v*2.23694);
const kmhToMph=v=>v==null?null:Math.round(v*0.621371);
const paToIn=v=>v==null?null:Math.round(v*0.0002952998*100)/100;
const mToMi=v=>v==null?null:Math.round(v*0.000621371*10)/10;
const degDir=d=>{if(d==null)return'';return['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'][Math.round(d/22.5)%16];};
function wxIcon(text,day=true){
  const s=(text||'').toLowerCase();
  if(s.includes('thunder')||s.includes('storm'))return'storm';
  if(s.includes('snow')||s.includes('sleet')||s.includes('flurr'))return'snow';
  if(s.includes('fog')||s.includes('haze'))return'fog';
  if(s.includes('rain')||s.includes('shower')||s.includes('drizzle'))return'rain';
  if(s.includes('mostly cloudy')||s.includes('overcast')||s==='cloudy')return'cloudy';
  if(s.includes('partly'))return day?'pcloudy':'pcloudy_night';
  if(s.includes('clear')||s.includes('sunny'))return day?'clear':'clear_night';
  return day?'pcloudy':'pcloudy_night';
}
function heatIndex(f,rh){
  if(f==null)return null;
  if(f<80||rh==null)return f;
  const hi=-42.379+2.04901523*f+10.14333127*rh-0.22475541*f*rh-0.00683783*f*f-0.05481717*rh*rh+0.00122874*f*f*rh+0.00085282*f*rh*rh-0.00000199*f*f*rh*rh;
  return Math.round(hi);
}
function feelsLike(f,rh,wind){
  if(f==null)return null;
  if(f<=50&&wind!=null&&wind>=3)return Math.round(35.74+0.6215*f-35.75*Math.pow(wind,.16)+0.4275*f*Math.pow(wind,.16));
  return heatIndex(f,rh);
}

let primaryCache=null, cityCache=null, alertCache=null, lastFull=0, lastCities=0;

async function getPoint(lat,lon){return api(`https://api.weather.gov/points/${lat},${lon}`);}
async function getPrimary(){
  const p=await getPoint(PRIMARY.lat,PRIMARY.lon);
  const pr=p.properties;
  const stations=await api(pr.observationStations);
  const sid=stations.features?.[0]?.properties?.stationIdentifier;
  let obs=null;
  if(sid) obs=(await api(`https://api.weather.gov/stations/${sid}/observations/latest`)).properties;
  const forecast=await api(pr.forecast);
  const hourly=await api(pr.forecastHourly);
  const f0=forecast.properties.periods?.[0]||{};
  const temp=obs?.temperature?.value!=null?cToF(obs.temperature.value):f0.temperature;
  const rh=obs?.relativeHumidity?.value??null;
  const wind=obs?.windSpeed?.value!=null?kmhToMph(obs.windSpeed.value):null;
  const primary={
    name:'WISCONSIN RAPIDS',
    station_name:obs?.station?.split('/').pop()||sid||'NWS OBSERVATION',
    temp, condition:obs?.textDescription||f0.shortForecast||'',
    icon:wxIcon(obs?.textDescription||f0.shortForecast,true),
    humidity:rh==null?null:Math.round(rh),
    wind, wind_dir:degDir(obs?.windDirection?.value),
    feels_like:feelsLike(temp,rh,wind),
    dewpoint:obs?.dewpoint?.value!=null?cToF(obs.dewpoint.value):null,
    pressure:paToIn(obs?.barometricPressure?.value),
    visibility:mToMi(obs?.visibility?.value)
  };
  const periods=(hourly.properties.periods||[]).slice(0,24).map(x=>({
    name:x.name,temp:x.temperature,short:x.shortForecast,icon:wxIcon(x.shortForecast,x.isDaytime),
    precip:x.probabilityOfPrecipitation?.value??0,label:new Date(x.startTime).toLocaleTimeString([], {hour:'numeric'})
  }));
  const days=buildDays(forecast.properties.periods||[]);
  return {primary,periods,hourly:periods,hours:periods,days,date_label:new Date().toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'}).toUpperCase(),updated_label:new Date().toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})};
}
function buildDays(ps){
  const out=[];
  for(let i=0;i<ps.length&&out.length<7;){
    const p=ps[i];
    if(p.isDaytime){
      const n=ps[i+1];
      out.push({dow:p.name,short_date:new Date(p.startTime).toLocaleDateString('en-US',{month:'short',day:'numeric'}).toUpperCase(),hi:p.temperature,lo:n?.temperature??null,short:p.shortForecast,icon:wxIcon(p.shortForecast,true),precip:p.probabilityOfPrecipitation?.value??0});
      i+=2;
    }else{
      out.push({dow:'TONIGHT',short_date:new Date(p.startTime).toLocaleDateString('en-US',{month:'short',day:'numeric'}).toUpperCase(),hi:null,lo:p.temperature,short:p.shortForecast,icon:wxIcon(p.shortForecast,false),precip:p.probabilityOfPrecipitation?.value??0});
      i++;
    }
  }
  return out;
}

async function getAlerts(){
  const j=await api('https://api.weather.gov/alerts/active?area=WI');
  return (j.features||[]).map(f=>{
    const p=f.properties||{};
    return {event:p.event||'WEATHER ALERT',headline:p.headline||p.event||'',areas:p.areaDesc||'',text:p.description||'',instruction:p.instruction||'',expires_label:p.expires?new Date(p.expires).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'}):'--'};
  });
}
async function getCities(){
  const results=await Promise.all(CITY_POINTS.map(async ([name,lat,lon])=>{
    try{
      const p=await getPoint(lat,lon), st=await api(p.properties.observationStations), sid=st.features?.[0]?.properties?.stationIdentifier;
      if(!sid)return{name,lat,lon,temp:null,icon:'pcloudy'};
      const o=(await api(`https://api.weather.gov/stations/${sid}/observations/latest`)).properties;
      const temp=cToF(o.temperature?.value);
      return{name,lat,lon,temp,icon:wxIcon(o.textDescription,true)};
    }catch(e){return{name,lat,lon,temp:null,icon:'pcloudy'};}
  }));
  return results.filter(x=>x.temp!=null);
}

async function loadData(){
  const now=Date.now();
  if(!primaryCache||now-lastFull>55000){
    primaryCache=await getPrimary();
    try{alertCache=await getAlerts();}catch(e){alertCache=alertCache||[];}
    lastFull=now;
  }
  if(!cityCache||now-lastCities>300000){
    cityCache=await getCities();
    lastCities=now;
  }
  const d={...primaryCache,alerts:alertCache||[],cities:cityCache||[]};
  document.body.classList.remove('nodata');
  return d;
}
function boot(render){
  const run=async()=>{
    try{
      const d=await loadData();
      render(d);
      const s=$('#stamp');if(s)s.textContent=`UPDATED ${d.updated_label} · NWS`;
    }catch(e){
      document.body.classList.add('nodata');
      console.error('Online NWS feed error:',e);
    }
  };
  run();
  setInterval(run,REFRESH_MS);
}
