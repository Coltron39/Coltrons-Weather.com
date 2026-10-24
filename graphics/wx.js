/* ============================================================
   COLTRONS FIRST ALERT WEATHER - shared graphics engine
   Loads data/wx.json (written by wx_feed.py), redraws every
   REFRESH_MS, and draws the weather icons as inline SVG.
   ============================================================ */

const REFRESH_MS = 15000;
const DATA_URL = 'data/wx.json';

/* ---------------- weather icons (inline SVG, no image files) ---------------- */
const ICONS = {
  clear: `<circle class="sun" cx="50" cy="50" r="19"/>
    <g stroke="#ffcf3f" stroke-width="6" stroke-linecap="round">
      <line x1="50" y1="12" x2="50" y2="22"/><line x1="50" y1="78" x2="50" y2="88"/>
      <line x1="12" y1="50" x2="22" y2="50"/><line x1="78" y1="50" x2="88" y2="50"/>
      <line x1="24" y1="24" x2="31" y2="31"/><line x1="69" y1="69" x2="76" y2="76"/>
      <line x1="24" y1="76" x2="31" y2="69"/><line x1="69" y1="31" x2="76" y2="24"/>
    </g>`,
  clear_night: `<path class="moon" d="M62 20a32 32 0 1 0 20 45A34 34 0 0 1 62 20z"/>
    <circle class="moon" cx="26" cy="26" r="2.5"/><circle class="moon" cx="80" cy="30" r="2"/>`,
  pcloudy: `<circle class="sun" cx="38" cy="36" r="15"/>
    <g stroke="#ffcf3f" stroke-width="5" stroke-linecap="round">
      <line x1="38" y1="8" x2="38" y2="15"/><line x1="10" y1="36" x2="17" y2="36"/>
      <line x1="18" y1="16" x2="23" y2="21"/><line x1="58" y1="16" x2="53" y2="21"/>
    </g>
    <path class="cloud" d="M38 78h34a15 15 0 0 0 1-30 21 21 0 0 0-39-5 14 14 0 0 0 4 35z"/>`,
  pcloudy_night: `<path class="moon" d="M52 18a24 24 0 1 0 15 34A26 26 0 0 1 52 18z"/>
    <path class="cloud" d="M34 80h38a16 16 0 0 0 1-31 22 22 0 0 0-41-5 15 15 0 0 0 2 36z"/>`,
  cloudy: `<path class="cloud-dk" d="M30 52a19 19 0 0 1 35-9 16 16 0 0 1 3 30H32a13 13 0 0 1-2-21z"/>
    <path class="cloud" d="M36 82h40a16 16 0 0 0 1-31 22 22 0 0 0-41-5 15 15 0 0 0 0 36z"/>`,
  rain: `<path class="cloud" d="M34 62h38a16 16 0 0 0 1-31 22 22 0 0 0-41-5 15 15 0 0 0 2 36z"/>
    <g class="drop"><rect x="34" y="70" width="5" height="18" rx="2.5"/>
    <rect x="52" y="74" width="5" height="18" rx="2.5"/>
    <rect x="70" y="70" width="5" height="18" rx="2.5"/></g>`,
  storm: `<path class="cloud-dk" d="M32 60h38a16 16 0 0 0 1-31 22 22 0 0 0-41-5 15 15 0 0 0 2 36z"/>
    <path class="bolt" d="M52 62 36 90h13l-4 18 22-30H53l6-16z"/>`,
  snow: `<path class="cloud" d="M34 60h38a16 16 0 0 0 1-31 22 22 0 0 0-41-5 15 15 0 0 0 2 36z"/>
    <g class="flake" stroke-width="4" stroke-linecap="round">
      <line x1="38" y1="72" x2="38" y2="88"/><line x1="30" y1="80" x2="46" y2="80"/>
      <line x1="66" y1="72" x2="66" y2="88"/><line x1="58" y1="80" x2="74" y2="80"/>
    </g>`,
  fog: `<path class="cloud" d="M34 54h38a16 16 0 0 0 1-31 22 22 0 0 0-41-5 15 15 0 0 0 2 36z"/>
    <g stroke="#cfe2f5" stroke-width="6" stroke-linecap="round">
      <line x1="24" y1="68" x2="80" y2="68"/><line x1="32" y1="82" x2="88" y2="82"/>
    </g>`,
  wind: `<g stroke="#dff1ff" stroke-width="7" stroke-linecap="round" fill="none">
      <path d="M14 38h48a13 13 0 1 0-13-13"/>
      <path d="M14 62h58a13 13 0 1 1-13 13"/>
      <path d="M20 84h30"/>
    </g>`,
};

function icon(key, size) {
  const body = ICONS[key] || ICONS.pcloudy;
  return `<svg class="wxicon" width="${size}" height="${size}" viewBox="0 0 100 100">${body}</svg>`;
}

/* ---------------- helpers ---------------- */
const $ = (sel) => document.querySelector(sel);
const num = (v, dash = '--') => (v === null || v === undefined ? dash : v);

function tempClass(t) {
  if (t === null || t === undefined) return 'c-na';
  if (t >= 95) return 'c-extreme';
  if (t >= 80) return 'c-hot';
  if (t >= 65) return 'c-warm';
  if (t >= 50) return 'c-mild';
  if (t >= 33) return 'c-cool';
  if (t >= 15) return 'c-cold';
  return 'c-frigid';
}

function startClock() {
  const el = $('#clock'), dt = $('#date');
  const tick = () => {
    const d = new Date();
    let h = d.getHours() % 12 || 12;
    const m = String(d.getMinutes()).padStart(2, '0');
    const ap = d.getHours() >= 12 ? 'PM' : 'AM';
    if (el) el.textContent = `${h}:${m} ${ap}`;
    if (dt) dt.textContent = d.toLocaleDateString('en-US',
      { weekday: 'long', month: 'long', day: 'numeric' }).toUpperCase();
  };
  tick();
  setInterval(tick, 1000);
}

/* Build the standard station header into any element with id="header" */
function mountHeader(subtitle) {
  const h = $('#header');
  if (!h) return;
  h.className = 'header';
  h.innerHTML = `
    <div class="logo-mark" aria-label="Coltrons First Alert Weather"></div>
    <div class="logo-text">
      <div class="l1">COLTRONS <em>FIRST ALERT</em> WEATHER</div>
      <div class="l2">${subtitle || "WISCONSIN'S WEATHER AUTHORITY"}</div>
    </div>
    <div class="header-right">
      <div class="clock" id="clock">--:--</div>
      <div class="date" id="date"></div>
    </div>`;
  startClock();
}

/* Standard bottom bar. msg = rotating text, set by each page. */
function mountFooter(msg) {
  const f = $('#footer');
  if (!f) return;
  f.className = 'footer';
  f.innerHTML = `
    <div class="brandchip">FIRST ALERT WX</div>
    <div class="msg" id="footmsg">${msg || ''}</div>
    <div class="stamp" id="stamp">UPDATED --:--</div>`;
}

/* ---------------- data plumbing ---------------- */
let LAST = null;

async function loadData() {
  try {
    const r = await fetch(`${DATA_URL}?t=${Date.now()}`, { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    LAST = await r.json();
    document.body.classList.remove('nodata');
    return LAST;
  } catch (e) {
    document.body.classList.add('nodata');
    console.warn('wx.json unavailable:', e.message);
    return LAST;
  }
}

/* Every page calls this once: render(data) will be re-run on each refresh. */
function boot(render) {
  const run = async () => {
    const d = await loadData();
    if (!d) return;
    try { render(d); } catch (e) { console.error(e); }
    const s = $('#stamp');
    if (s) s.textContent = `UPDATED ${d.updated_label} \u00b7 NWS`;
  };
  run();
  setInterval(run, REFRESH_MS);
}

/* Rotate through an array of strings inside an element */
function rotate(el, items, ms = 6000) {
  if (!el || !items.length) return;
  let i = 0;
  el.textContent = items[0];
  if (items.length === 1) return;
  setInterval(() => {
    i = (i + 1) % items.length;
    el.style.opacity = 0;
    setTimeout(() => { el.textContent = items[i]; el.style.opacity = 1; }, 260);
  }, ms);
}
