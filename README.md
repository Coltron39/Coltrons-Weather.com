# COLTRONS FIRST ALERT WEATHER — On‑Air Package

A complete broadcast graphics package for your OBS weather station, covering all of
Wisconsin with live National Weather Service data. Nothing to sign up for, no API keys.

```
coltrons_first_alert/
├── wx_feed.py               ← live data service + local web server (run this first)
├── tv_master_control_v2.py  ← your controller, upgraded with weather scenes
├── README.md
└── graphics/
    ├── index.html           preview dashboard (open in a normal browser)
    ├── open.html            station open / cold open
    ├── current.html         CURRENT CONDITIONS
    ├── radar.html           animated DOPPLER RADAR loop
    ├── hourly.html          HOUR BY HOUR temperature trend
    ├── sevenday.html        7 DAY FORECAST
    ├── statewide.html       WISCONSIN TEMPERATURES map
    ├── alert.html           watches / warnings full screen
    ├── lowerthird.html      ★ transparent overlay — weather bar + crawl
    ├── bug.html             ★ transparent overlay — corner temp bug
    ├── style.css, wx.js, wimap.js, wi.geojson
    └── data/wx.json         written by wx_feed.py
```

★ = transparent background, meant to sit **on top of** your camera/desk scenes.

---

## 1. Start the data feed

```bash
cd coltrons_first_alert
python3 wx_feed.py
```

It does two jobs:

1. Pulls live data from the National Weather Service every 5 minutes and writes
   `graphics/data/wx.json`.
2. Serves the `graphics/` folder at **http://127.0.0.1:8080/** with caching turned
   off, which is what OBS browser sources need.

Leave that terminal open the whole time you're on the air. Every graphic refetches
the data every 15 seconds, so numbers update live without touching OBS.

**One thing to edit before your first show** — open `wx_feed.py` and put your own
email in `USER_AGENT`. The NWS asks for a contact address in API requests:

```python
USER_AGENT = "ColtronsFirstAlertWeather/1.0 (you@example.com)"
```

Other settings at the top of that file:

| Setting | What it does |
|---|---|
| `PRIMARY` | Your home city — currently Wisconsin Rapids (44.3836, ‑89.8173) |
| `CITIES` | The 16 Wisconsin cities on the statewide map and in the crawl |
| `ALERT_AREA` | `"WI"` — statewide watches and warnings |
| `POLL_SECONDS` | 300 (5 min). Don't go below 60. |
| `SERVE_PORT` | 8080 |
| `STATION_NAME` / `STATION_SLOGAN` | Branding on every graphic |

Sanity check: visit **http://127.0.0.1:8080/index.html** in Chrome. You should see
live thumbnails of all nine graphics.

---

## 2. Add the graphics to OBS

For every page, make a scene and add **one Browser source** set up like this:

- **Width 1920, Height 1080**
- **URL** `http://127.0.0.1:8080/<page>.html`
- ✅ Refresh browser when scene becomes active
- ☐ **Shutdown source when not visible** — leave this **OFF** (otherwise the radar
  loop and the clock restart every time you cut to it)
- Custom CSS: leave the default alone, or clear it — the pages style themselves
- Control audio via OBS: not needed, the graphics are silent

**Scenes you already have** — point each one's browser source here:

| Scene name (exact) | URL |
|---|---|
| `RADAR` | `http://127.0.0.1:8080/radar.html` |
| `SEVENDAY` | `http://127.0.0.1:8080/sevenday.html` |
| `STATEWIDE` | `http://127.0.0.1:8080/statewide.html` |
| `WEATHER` | your camera + `lowerthird.html` on top |
| `PROGRAM` | whatever you're using it for now |

**Optional scenes** — the panel already has greyed‑out buttons waiting for these. Build one, hit RESCAN, and the button turns on:

| Scene name (exact) | URL |
|---|---|
| `CURRENT` | `http://127.0.0.1:8080/current.html` |
| `HOURLY` | `http://127.0.0.1:8080/hourly.html` |
| `ALERT` | `http://127.0.0.1:8080/alert.html` |
| `STATION ID` | `http://127.0.0.1:8080/open.html` |
| `COMMERCIAL` | `http://127.0.0.1:8080/commercial.html` (break slate + countdown) |
| `ADS` | `http://127.0.0.1:8080/ads.html` (rotating ad reel) |
| `NEWS DESK` | `http://127.0.0.1:8080/desk_split.html` (two-box anchor layout) |
| `OVERNIGHT` | `http://127.0.0.1:8080/overnight.html` (bed time slate) |

Scene names have to match exactly — that's the string the controller sends to OBS.

**The two overlays** go inside your existing scenes rather than in scenes of their own:

- `lowerthird.html` → add to `WEATHER` (and `NEWS DESK` if you like) on top of the
  camera. Toggle its eye icon to bring the bar in and out.
- `sponsor.html` → "WEATHER SPONSORED BY" box that slides in and out on its own. Add
  it to `WEATHER`, `RADAR`, or any scene you want monetized.
- `bug.html` → add it to **every** scene you want branded. Easiest way: build it
  once, then right‑click → Copy, and in each other scene right‑click → Paste
  (Reference), so one edit updates them all.

Tip: put your weather graphics in a **Studio Mode** preview before cutting if you
want a look first — the controller cuts straight to program.

---

## 3. Run the upgraded controller

```bash
pip install obsws-python
python3 tv_master_control_v2.py
```

Put your OBS WebSocket password in `OBS_PASSWORD` first (OBS → Tools → WebSocket
Server Settings → Show Connect Info).

The panel is built around the five scenes you have today — **PROGRAM, WEATHER, RADAR,
SEVENDAY, STATEWIDE** — on the top row, hotkeys `1`–`5` (or `F1`–`F5`).

- **It reads your real scene list.** On connect it asks OBS what scenes exist, lights
  up those buttons, and greys out everything else so you can't fire a dead scene by
  accident. Add a scene in OBS → press **RESCAN** (or `F12`) → the button goes live.
  It also tells you about scenes in OBS that aren't on the panel yet.
- **AUTO WEATHER BLOCK** (`Space`) — hands‑free rotation, skipping anything that
  doesn't exist. With your current scenes that's Weather 20s → Radar 26s →
  Statewide 18s → Sevenday 22s, looping. Edit `WEATHER_BLOCK` to change it.
- **FIRST ALERT WATCH** — reads `wx.json` every 5 seconds and cuts to the first
  available scene from `ALERT → BREAKING NEWS → RADAR → WEATHER` when a new
  Wisconsin warning drops. Right now that lands on `RADAR`; build an `ALERT` scene
  and it'll use that instead automatically.
- **Feed light** — whether `wx_feed.py` is running, whether the data's gone stale, and
  how many alerts are active.
- Stream start/stop next to your recording buttons.

---

## 4. A show rundown that works

A tight 2‑minute weathercast with the scenes you have:

| Time | Scene | Notes |
|---|---|---|
| 0:00 | `WEATHER` + lower third | you on camera, tease the headline |
| 0:25 | `RADAR` | walk the loop — last 50 minutes |
| 0:55 | `STATEWIDE` | who's warmest / coolest in Wisconsin |
| 1:20 | `SEVENDAY` | the payoff — hit the pattern change |
| 1:50 | `WEATHER` + lower third | wrap and toss |
| 2:05 | `PROGRAM` | |

Unattended: press `Space` to start the auto weather block and leave FIRST ALERT WATCH
on. It runs itself and breaks in on warnings.

Severe weather: once you build an `ALERT` scene, `alert.html` shows the event name,
the counties, the NWS safety instruction, and a crawl; when nothing is active it shows
a green ALL CLEAR card, so it's always safe to cut to. Until then, park on `RADAR`
with the lower third up.

---

## 5. The news desk

Two ways to do it, pick whichever matches your shot.

**`desk.html` — full-frame overlay.** Your camera fills the whole 1920x1080 frame and
this page draws the furniture on top: station slug top-left, clock and live temperature
top-right, a blinking LIVE flag, a rotating headline band across the bottom, and a
ticker crawl. It's transparent, so add it as a browser source *above* your camera
inside the `NEWS DESK` scene. This is the one to use if you're just talking to camera.

**`desk_split.html` — two-box layout.** A full scene with a framed window for your
camera on the left and an over-the-shoulder panel on the right that changes graphics as
the headline changes. Also gets a name plate, headline band and ticker.

For the two-box version the camera window is a real hole cut out of the background, so
your camera source goes **below** the browser source in the list. Set its transform to
exactly:

| | |
|---|---|
| Position X | 56 |
| Position Y | 214 |
| Width | 1096 |
| Height | 616 |

In OBS: right-click your camera → Transform → Edit Transform, type those in, then drag
the browser source above the camera in the source list. The alignment numbers printed
inside the window fade out after 25 seconds so they're never on air over your face.
If your camera isn't 16:9, set Bounding Box Type to "Scale to inner bounds" and
Alignment to Center so nothing stretches.

**Clock mode.** `desk.html` ships with `SHOW_MODE = "clock"` and tonight's rundown
(`rundown_2026-08-24.md`) built in. Each `STORIES` entry has an `at` time like `"21:08"`,
and the overlay switches headlines by the wall clock so the graphics follow your show
sheet without you touching anything. Before the first entry it shows the `PRESHOW` card;
after the last it shows `POSTSHOW`. Rehearse any moment with `desk.html?now=21:13`.
Set `SHOW_MODE = "rotate"` to go back to simple cycling every `STORY_SECONDS`.

**Editing the rundown.** Both pages have a `SEGMENTS` (or `STORIES`) array at the top.
Each entry is one headline: `topic` is the small tab, `wx:true` turns that tab red,
`hl` is the big headline, and on the two-box page `pane` picks which over-the-shoulder
graphic goes with it — `1` current conditions, `2` city temps, `3` next few days,
`4` your own bullet points from the `BULLETS` array. They rotate every 15 seconds;
change `SEGMENT_SECONDS` to taste. `ANCHOR`, `ROLE` and `FROMLINE` set the name plate.

The ticker builds itself from `TICKER_LINES` plus live data — tonight's forecast, any
active warnings, and city temperatures — so it stays current without you touching it.

---

## 6. Bed time and the desk widget

**`overnight.html`** is the sign-off slate. It reads BED TIME with a countdown to 8 AM,
your live current temperature and the overnight low, and a slow drifting star field so
it isn't a dead frame for eleven hours. At 8:00 AM it turns itself into a GOOD MORNING
card with a sunrise palette — no second scene needed. Times live at the top of the file
as `BED_TIME` and `REOPEN`. Rehearse any hour with `overnight.html?now=03:20`.

Build an `OVERNIGHT` scene pointed at it and that's your whole night.

**`wx_widget.py`** is a small always-on-top panel to keep in the corner of your screen:

| Button | What it does |
|---|---|
| WEATHER ANIMATION | Loops WEATHER 20s → RADAR 26s → STATEWIDE 18s → SEVENDAY 22s. Press again to stop and return to the scene you were on. Space bar also toggles it. |
| BED TIME | Cuts to `OVERNIGHT`. |
| BACK ON AIR | Cuts to `PROGRAM`. |
| AUTO | Handles it for you: slate at 9 PM, program at 8 AM. Ticking it after 9 PM puts the slate up immediately. |

Run it with `python3 wx_widget.py`. It uses the same OBS WebSocket password as the
master control panel, and it skips any scene that doesn't exist in OBS, so it can't
cut you to a dead scene. Timings are the `ANIMATION` list at the top of the file.

---

## 7. Commercials

Three pieces, all with their config at the top of the file:

**`commercial.html`** — the break slate. "WE'LL BE RIGHT BACK", a countdown that
restarts every time OBS shows the source, a progress bar, live current/tonight
conditions, and a sponsor rail. Edit `BREAK_SECONDS` (default 120), `NEXT_SEGMENT`,
and `SPONSORS`. At 15 seconds left the label flips to "STAND BY ‑ HOT MIC" so you
know to get set.

**`ads.html`** — the actual ad reel. Full‑screen spots that auto‑advance, each with its
own color scheme, logo block, headline, offer, hours and phone. It carries a PAID
ADVERTISEMENT disclosure, your station bug, progress dots, and a running break clock.
Edit the `SPOTS` array — each entry takes `seconds`, `cat`, `name`, `tag`, `offer`,
`meta`, `initials`, and colors (`bg`, `ink`, `accent`, `markbg`, `markink`). Add
`center: true` for a centered layout. The four sample businesses are placeholders —
swap in real advertisers, and the last card is a house ad selling the spots.

**`sponsor.html`** — transparent overlay that slides a "WEATHER SPONSORED BY" box in
for 12 seconds every 25, cycling your sponsor list. Drop it over any scene.

How to run a break: cut to `ADS` and let the reel play, or cut to `COMMERCIAL` for a
single slate. If you use both, put the ad reel first and the slate last so the
countdown lands right before you come back.

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Graphics blank / "WAITING FOR DATA" | `wx_feed.py` isn't running, or the port changed |
| Numbers frozen | Check the feed terminal for errors; NWS occasionally 503s and it retries |
| Radar loop restarts on every cut | "Shutdown source when not visible" is still checked |
| Fonts look wrong | The pages pull Barlow Condensed + Inter from Google Fonts — needs internet |
| Clock is off | The graphics use your PC's local clock and timezone |
| Nothing switches | OBS scene names must match the table above, character for character - press RESCAN to see what OBS actually reports |

---

## 9. Data sources and attribution

- Current conditions, hourly and 7‑day forecasts, watches and warnings:
  [NOAA / National Weather Service API](https://api.weather.gov) — public, no key
  required, User‑Agent header required. See the
  [NWS API docs](https://www.weather.gov/documentation/services-web-api).
- Radar imagery: NEXRAD N0Q base reflectivity tiles from the
  [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu/ogc/), Iowa State
  University, which republishes NOAA radar mosaics.
- Basemap: [CARTO dark basemap](https://carto.com/basemaps/) with
  [OpenStreetMap](https://www.openstreetmap.org/copyright) data.
- Wisconsin state outline: [US states GeoJSON](https://github.com/glynnbird/usstatesgeojson),
  simplified.
- Map rendering: [Leaflet 1.9.4](https://leafletjs.com/).

Every graphic already carries a "WEATHER DATA: NOAA / NATIONAL WEATHER SERVICE"
credit in the footer, which keeps you square with the attribution terms.
