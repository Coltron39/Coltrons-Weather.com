#!/usr/bin/env python3
"""
COLTRONS FIRST ALERT WEATHER - live data feed + graphics web server.

What it does:
  1. Every POLL_SECONDS it pulls live data from the National Weather Service
     (api.weather.gov - free, no API key, official government source).
  2. Writes everything into graphics/data/wx.json
  3. Serves the graphics/ folder on http://127.0.0.1:8080 so your OBS
     Browser Sources can read it.

Run it BEFORE you go on air:      python wx_feed.py
Leave it running the whole show. Ctrl+C to stop.

Requires: nothing but Python 3 (uses only the standard library).
"""

import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# ============================ CONFIG ============================
STATION_NAME = "COLTRONS FIRST ALERT WEATHER"
STATION_SLOGAN = "WISCONSIN'S WEATHER AUTHORITY"

# Your main / hometown city. This drives the big "current conditions",
# the 7-day forecast and the hourly strip.
PRIMARY = {
    "name": "WISCONSIN RAPIDS",
    "lat": 44.3836,
    "lon": -89.8173,
}

# The city-by-city statewide board. Add/remove freely.
CITIES = [
    ("SUPERIOR",         46.7208, -92.1041),
    ("ASHLAND",          46.5924, -90.8834),
    ("RHINELANDER",      45.6366, -89.4121),
    ("WAUSAU",           44.9591, -89.6301),
    ("EAU CLAIRE",       44.8113, -91.4985),
    ("STEVENS POINT",    44.5236, -89.5746),
    ("WISCONSIN RAPIDS", 44.3836, -89.8173),
    ("GREEN BAY",        44.5133, -88.0133),
    ("APPLETON",         44.2619, -88.4154),
    ("LA CROSSE",        43.8014, -91.2396),
    ("FOND DU LAC",      43.7730, -88.4470),
    ("SHEBOYGAN",        43.7508, -87.7145),
    ("MADISON",          43.0731, -89.4012),
    ("MILWAUKEE",        43.0389, -87.9065),
    ("JANESVILLE",       42.6828, -89.0187),
    ("KENOSHA",          42.5847, -87.8212),
]

ALERT_AREA = "WI"          # state code for active alerts
POLL_SECONDS = 300         # 5 minutes (never go below 60 - be kind to NWS)
SERVE_PORT = 8080
SERVE_GRAPHICS = True      # set False if you'd rather host the files yourself

# NWS asks for a contact in the User-Agent. Put your email in here.
USER_AGENT = "ColtronsFirstAlertWeather/1.0 (contact@example.com)"
# ================================================================

BASE = os.path.dirname(os.path.abspath(__file__))
GRAPHICS_DIR = os.path.join(BASE, "graphics")
DATA_DIR = os.path.join(GRAPHICS_DIR, "data")
OUT_FILE = os.path.join(DATA_DIR, "wx.json")

_point_cache = {}


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def get_json(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
            )
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if attempt == tries - 1:
                log(f"  ! failed {url.split('api.weather.gov')[-1]} -> {e}")
                return None
            time.sleep(2 + attempt * 2)
    return None


def c_to_f(c):
    return None if c is None else round(c * 9 / 5 + 32)


def kmh_to_mph(k):
    return None if k is None else round(k * 0.621371)


def deg_to_compass(d):
    if d is None:
        return ""
    pts = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return pts[int((d % 360) / 22.5 + 0.5) % 16]


def icon_key(nws_icon_url, short_text=""):
    """Turn an NWS icon URL / description into a simple key our SVGs understand."""
    src = f"{nws_icon_url or ''} {short_text or ''}".lower()
    night = "/night/" in (nws_icon_url or "").lower()
    if any(w in src for w in ("tsra", "thunder")):
        return "storm"
    if any(w in src for w in ("blizzard", "snow", "sleet", "flurries", "ice", "fzra")):
        return "snow"
    if any(w in src for w in ("rain", "shower", "drizzle", "rain_showers")):
        return "rain"
    if any(w in src for w in ("fog", "haze", "smoke", "dust")):
        return "fog"
    if "wind" in src:
        return "wind"
    if any(w in src for w in ("ovc", "overcast", "cloudy")) and "partly" not in src and "mostly sunny" not in src:
        return "cloudy"
    if any(w in src for w in ("bkn", "sct", "partly", "mostly cloudy", "mostly clear")):
        return "pcloudy_night" if night else "pcloudy"
    if any(w in src for w in ("skc", "few", "clear", "sunny", "hot")):
        return "clear_night" if night else "clear"
    return "pcloudy_night" if night else "pcloudy"


def point_meta(lat, lon):
    key = (round(lat, 4), round(lon, 4))
    if key in _point_cache:
        return _point_cache[key]
    d = get_json(f"https://api.weather.gov/points/{lat},{lon}")
    if not d:
        return None
    p = d["properties"]
    meta = {
        "forecast": p.get("forecast"),
        "hourly": p.get("forecastHourly"),
        "stations": p.get("observationStations"),
        "radar": p.get("radarStation"),
        "city": (p.get("relativeLocation", {}).get("properties", {}) or {}).get("city", ""),
    }
    _point_cache[key] = meta
    return meta


def latest_observation(stations_url):
    """Walk the nearest stations until one gives us a usable temperature."""
    st = get_json(stations_url)
    if not st:
        return None
    for feat in (st.get("features") or [])[:4]:
        sid = feat["properties"]["stationIdentifier"]
        ob = get_json(f"https://api.weather.gov/stations/{sid}/observations/latest")
        if not ob:
            continue
        p = ob.get("properties", {})
        temp = (p.get("temperature") or {}).get("value")
        if temp is None:
            continue
        wind_k = (p.get("windSpeed") or {}).get("value")
        gust_k = (p.get("windGust") or {}).get("value")
        return {
            "station": sid,
            "station_name": feat["properties"].get("name", sid),
            "temp": c_to_f(temp),
            "condition": (p.get("textDescription") or "").upper() or "N/A",
            "icon": icon_key(p.get("icon"), p.get("textDescription")),
            "dewpoint": c_to_f((p.get("dewpoint") or {}).get("value")),
            "humidity": (lambda v: None if v is None else round(v))((p.get("relativeHumidity") or {}).get("value")),
            "wind": kmh_to_mph(wind_k) or 0,
            "gust": kmh_to_mph(gust_k),
            "wind_dir": deg_to_compass((p.get("windDirection") or {}).get("value")),
            "feels_like": c_to_f((p.get("heatIndex") or {}).get("value"))
                          or c_to_f((p.get("windChill") or {}).get("value")),
            "pressure": (lambda v: None if v is None else round(v / 3386.39, 2))(
                (p.get("barometricPressure") or {}).get("value")),
            "visibility": (lambda v: None if v is None else round(v / 1609.34))(
                (p.get("visibility") or {}).get("value")),
        }
    return None


def build_periods(forecast_url):
    d = get_json(forecast_url)
    if not d:
        return []
    out = []
    for p in d["properties"]["periods"]:
        out.append({
            "name": p["name"].upper(),
            "start": p["startTime"],
            "is_day": p["isDaytime"],
            "temp": p["temperature"],
            "short": p["shortForecast"].upper(),
            "detailed": p["detailedForecast"],
            "precip": (p.get("probabilityOfPrecipitation") or {}).get("value") or 0,
            "wind": f"{p.get('windDirection','')} {p.get('windSpeed','')}".strip(),
            "icon": icon_key(p.get("icon"), p["shortForecast"]),
        })
    return out


def build_days(periods):
    """Fold day/night periods into 7 hi/lo days."""
    days, order = {}, []
    for p in periods:
        date = p["start"][:10]
        if date not in days:
            days[date] = {"date": date, "hi": None, "lo": None,
                          "short": "", "icon": "pcloudy", "precip": 0, "label": ""}
            order.append(date)
        d = days[date]
        if p["is_day"]:
            d["hi"] = p["temp"]
            d["short"] = p["short"]
            d["icon"] = p["icon"]
            d["label"] = p["name"]
            d["precip"] = max(d["precip"], p["precip"])
        else:
            d["lo"] = p["temp"]
            d["precip"] = max(d["precip"], p["precip"])
            if d["hi"] is None:          # tonight-only first period
                d["short"] = p["short"]
                d["icon"] = p["icon"]
                d["label"] = p["name"]
    result = []
    for i, date in enumerate(order[:7]):
        d = days[date]
        dt = datetime.strptime(date, "%Y-%m-%d")
        dow = "TODAY" if i == 0 else dt.strftime("%A").upper()[:3]
        d["dow"] = dow
        d["short_date"] = dt.strftime("%-m/%-d") if os.name != "nt" else dt.strftime("%m/%d")
        result.append(d)
    return result


def build_hourly(hourly_url, hours=12):
    d = get_json(hourly_url)
    if not d:
        return []
    out = []
    for p in d["properties"]["periods"][:hours]:
        dt = datetime.fromisoformat(p["startTime"])
        label = dt.strftime("%-I%p") if os.name != "nt" else dt.strftime("%I%p").lstrip("0")
        out.append({
            "label": label.replace("AM", "A").replace("PM", "P"),
            "temp": p["temperature"],
            "short": p["shortForecast"].upper(),
            "precip": (p.get("probabilityOfPrecipitation") or {}).get("value") or 0,
            "icon": icon_key(p.get("icon"), p["shortForecast"]),
        })
    return out


SEVERE = {
    "tornado warning": ("TORNADO WARNING", 5),
    "severe thunderstorm warning": ("SEVERE T-STORM WARNING", 4),
    "flash flood warning": ("FLASH FLOOD WARNING", 4),
    "blizzard warning": ("BLIZZARD WARNING", 4),
    "ice storm warning": ("ICE STORM WARNING", 4),
    "winter storm warning": ("WINTER STORM WARNING", 3),
}


def build_alerts():
    d = get_json(f"https://api.weather.gov/alerts/active?area={ALERT_AREA}")
    if not d:
        return []
    out = []
    for f in d.get("features", []):
        p = f["properties"]
        event = (p.get("event") or "").strip()
        lvl = SEVERE.get(event.lower(), (event.upper(), 1))[1]
        if "warning" in event.lower():
            lvl = max(lvl, 4)
        elif "watch" in event.lower():
            lvl = max(lvl, 3)
        elif "advisory" in event.lower():
            lvl = max(lvl, 2)
        exp = p.get("ends") or p.get("expires") or ""
        try:
            exp_label = datetime.fromisoformat(exp).strftime("%-I:%M %p").upper() if exp else ""
        except Exception:
            exp_label = ""
        counties = re.sub(r"\s*,\s*", ", ", p.get("areaDesc", "")).upper()
        out.append({
            "event": event.upper(),
            "level": lvl,
            "severity": (p.get("severity") or "").upper(),
            "urgency": (p.get("urgency") or "").upper(),
            "areas": counties,
            "headline": (p.get("headline") or "").upper(),
            "text": " ".join((p.get("description") or "").split())[:600],
            "instruction": " ".join((p.get("instruction") or "").split())[:400],
            "expires_label": exp_label,
        })
    out.sort(key=lambda a: -a["level"])
    return out


def build_cities():
    rows = []
    for name, lat, lon in CITIES:
        meta = point_meta(lat, lon)
        if not meta:
            continue
        ob = latest_observation(meta["stations"]) if meta.get("stations") else None
        if not ob:
            continue
        rows.append({
            "name": name,
            "lat": lat,
            "lon": lon,
            "temp": ob["temp"],
            "condition": ob["condition"],
            "icon": ob["icon"],
            "wind": ob["wind"],
            "wind_dir": ob["wind_dir"],
        })
        log(f"    {name:<18} {ob['temp']}\u00b0 {ob['condition']}")
    return rows


def collect():
    now = datetime.now()
    log("Updating weather data...")

    meta = point_meta(PRIMARY["lat"], PRIMARY["lon"])
    periods = build_periods(meta["forecast"]) if meta else []
    current = latest_observation(meta["stations"]) if meta else None
    hourly = build_hourly(meta["hourly"]) if meta else []
    if current:
        log(f"    {PRIMARY['name']:<18} {current['temp']}\u00b0 {current['condition']}")

    alerts = build_alerts()
    log(f"    active Wisconsin alerts: {len(alerts)}")

    cities = build_cities()

    data = {
        "station": {"name": STATION_NAME, "slogan": STATION_SLOGAN},
        "updated": now.isoformat(),
        "updated_label": (now.strftime("%-I:%M %p") if os.name != "nt"
                          else now.strftime("%I:%M %p").lstrip("0")).upper(),
        "date_label": now.strftime("%A, %B %-d" if os.name != "nt" else "%A, %B %d").upper(),
        "primary": {"name": PRIMARY["name"], **(current or {})},
        "periods": periods,
        "days": build_days(periods),
        "hourly": hourly,
        "cities": cities,
        "alerts": alerts,
        "radar_station": (meta or {}).get("radar", ""),
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = OUT_FILE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=1)
    os.replace(tmp, OUT_FILE)
    log(f"Wrote {os.path.relpath(OUT_FILE, BASE)}  ({len(cities)} cities, {len(alerts)} alerts)")
    if alerts:
        log(f"  >> TOP ALERT: {alerts[0]['event']} - {alerts[0]['areas'][:70]}")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


def serve():
    handler = partial(QuietHandler, directory=GRAPHICS_DIR)
    httpd = ThreadingHTTPServer(("127.0.0.1", SERVE_PORT), handler)
    log(f"Graphics server up  ->  http://127.0.0.1:{SERVE_PORT}/")
    httpd.serve_forever()


def main():
    print("=" * 62)
    print(f"  {STATION_NAME}")
    print("  live data feed  |  National Weather Service")
    print("=" * 62)
    os.makedirs(DATA_DIR, exist_ok=True)

    if SERVE_GRAPHICS:
        threading.Thread(target=serve, daemon=True).start()
        for page in ("current", "sevenday", "statewide", "radar",
                     "hourly", "alert", "lowerthird", "bug", "open"):
            print(f"    http://127.0.0.1:{SERVE_PORT}/{page}.html")
        print("=" * 62)

    while True:
        try:
            collect()
        except Exception as e:
            log(f"!! update failed: {e}")
        log(f"Next update in {POLL_SECONDS // 60} min. (Ctrl+C to stop)\n")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nFeed stopped. Off the air.")
