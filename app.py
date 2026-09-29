"""SatCrop Digital Twin: hackathon prototype.

Run with:  streamlit run app.py
Weather is live (Open-Meteo, or OpenWeatherMap with your own key). Land records, market prices and
scheme details are illustrative samples only.
"""
import html as _html
import math
import os
import random
import re
import zlib
from datetime import datetime, timedelta, timezone

import folium
import numpy as np
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="SatCrop Digital Twin", page_icon="🛰️",
                   layout="wide", initial_sidebar_state="expanded")

_VER = tuple(int(x) for x in st.__version__.split(".")[:2] if x.isdigit())
STRETCH = {"width": "stretch"} if _VER >= (1, 49) else {"use_container_width": True}

# ───────────────────────────── Styling ─────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Public+Sans:wght@400;500;600&display=swap');
:root{--ink:#16271D;--field:#2E6B45;--leaf:#6BAA75;--warn:#E8A33D;--danger:#D64933;
 /* Theme-adaptive tokens: they resolve against the current text colour, so they stay readable in Streamlit light AND dark themes. */
 --muted:color-mix(in srgb,currentColor 78%,transparent);
 --card-bg:color-mix(in srgb,currentColor 6%,transparent);
 --card-line:color-mix(in srgb,currentColor 22%,transparent);}
html,body,.stApp,p,li,label,input,textarea,button,td,th{font-family:'Public Sans',system-ui,sans-serif;}
h1,h2,h3,h4{font-family:'Bricolage Grotesque',system-ui,sans-serif !important;letter-spacing:-.01em;color:inherit;}
.block-container{padding-top:1.5rem;padding-bottom:3rem;max-width:1280px;}
textarea{font-family:ui-monospace,Menlo,Consolas,monospace !important;font-size:.82rem !important;line-height:1.5 !important;}
/* disabled text areas (live alert feed) are dimmed by default; keep them fully readable */
[data-testid="stTextArea"] textarea:disabled{color:inherit !important;-webkit-text-fill-color:currentColor !important;opacity:1 !important;}
[data-testid="stTextInput"] input::placeholder,[data-testid="stTextArea"] textarea::placeholder{opacity:.7;}

/* sidebar */
[data-testid="stSidebar"]{background:var(--ink);}
[data-testid="stSidebar"] *{color:#E4EDDD;}
[data-testid="stSidebar"] [role="radiogroup"]{gap:.2rem;}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:.6rem .85rem;border-radius:10px;width:100%;cursor:pointer;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:rgba(255,255,255,.07);}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:var(--field);}
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child{display:none;}
.brand{font-family:'Bricolage Grotesque',sans-serif;font-size:1.55rem;font-weight:700;margin:.2rem 0 .1rem;}
.brand-sub{font-size:.8rem;opacity:.7;margin-bottom:1.2rem;}
.side-note{font-size:.78rem;opacity:.75;line-height:1.5;border-top:1px solid rgba(255,255,255,.12);padding-top:.9rem;margin-top:1.4rem;}

/* hero */
.hero{display:flex;flex-wrap:wrap;gap:1.5rem;align-items:center;justify-content:space-between;
 padding:1.6rem 1.9rem;border-radius:20px;color:#F1F6EC;margin-bottom:1.1rem;background-color:var(--ink);
 background-image:repeating-radial-gradient(circle at 88% 15%,rgba(255,255,255,.06) 0 2px,transparent 2px 20px);}
.hero h1{color:#F7FAF3 !important;font-size:2.05rem;margin:0 0 .5rem;line-height:1.1;}
.chips{display:flex;flex-wrap:wrap;gap:.45rem;}
.chip{background:rgba(255,255,255,.12);padding:.22rem .7rem;border-radius:999px;font-size:.8rem;}
.hero-status{margin-top:.9rem;font-size:.95rem;opacity:.92;max-width:34rem;}
.ring{--p:50;--c:#E8A33D;width:132px;height:132px;border-radius:50%;flex:none;display:grid;place-items:center;
 background:conic-gradient(var(--c) calc(var(--p)*1%),rgba(255,255,255,.14) 0);}
.ring > div{width:106px;height:106px;border-radius:50%;background:var(--ink);display:flex;flex-direction:column;align-items:center;justify-content:center;}
.ring b{font-family:'Bricolage Grotesque',sans-serif;font-size:2.2rem;line-height:1;}
.ring span{font-size:.72rem;opacity:.75;margin-top:.15rem;}

/* pieces */
[data-testid="stMetric"]{background:var(--card-bg);border:1px solid var(--card-line);border-radius:12px;padding:.8rem 1rem;}
[data-testid="stMetricLabel"] p{color:var(--muted);font-size:.82rem;}
.page-title{font-family:'Bricolage Grotesque',sans-serif;font-size:2rem;font-weight:700;color:inherit;margin:0;}
.page-sub{color:var(--muted);margin:.15rem 0 1.2rem;}
.legend{display:flex;flex-wrap:wrap;gap:1rem;font-size:.8rem;color:var(--muted);margin:.5rem 0 0;}
.legend i{display:inline-block;width:.8rem;height:.8rem;border-radius:3px;margin-right:.35rem;vertical-align:-1px;box-shadow:0 0 0 1px var(--card-line);}
.banner{border-radius:14px;padding:1rem 1.2rem;margin-bottom:1rem;border-left:8px solid var(--c);background:var(--card-bg);border-top:1px solid var(--card-line);border-right:1px solid var(--card-line);border-bottom:1px solid var(--card-line);color:inherit;}
.banner b{font-family:'Bricolage Grotesque',sans-serif;font-size:1.25rem;}
.badge{display:inline-block;padding:.15rem .6rem;border-radius:6px;font-size:.74rem;font-weight:600;margin-right:.35rem;}
.b-Subsidy{background:#DDEFE0;color:#1E5232;}.b-Disaster{background:#F8DDD7;color:#8A2A1A;}
.b-Insurance{background:#DCE8F5;color:#1F4A78;}.b-Credit{background:#F6E9CC;color:#7A5410;}
.b-match{background:#16271D;color:#fff;}.b-hz{background:#F3E4D3;color:#7A4A1C;}
.scheme-name{font-family:'Bricolage Grotesque',sans-serif;font-size:1.15rem;font-weight:700;color:inherit;margin:.35rem 0 .15rem;}
.fit{font-size:.85rem;color:var(--muted);}
.alert-banner{display:flex;gap:.8rem;align-items:flex-start;border-radius:12px;padding:.75rem 1rem;margin-bottom:.55rem;color:#fff;background:var(--c);}
.alert-banner .ic{font-size:1.4rem;line-height:1.2;}
.alert-banner b{font-family:'Bricolage Grotesque',sans-serif;font-size:1.02rem;}
.alert-banner small{display:block;opacity:.92;font-size:.85rem;margin-top:.1rem;}
.alert-banner .tag{margin-left:auto;font-size:.7rem;font-weight:700;background:rgba(0,0,0,.22);padding:.1rem .55rem;border-radius:6px;white-space:nowrap;}
.clear-note{background:#E6F0E4;color:#1E5232;border-radius:12px;padding:.6rem 1rem;margin-bottom:.6rem;font-size:.88rem;}
.wx-src{font-size:.8rem;color:var(--muted);}
.ticker{overflow:hidden;background:var(--ink);color:#EAF3E4;border-radius:10px;padding:.5rem 0;margin-bottom:.7rem;white-space:nowrap;font-size:.88rem;}
.ticker-track{display:inline-block;padding-left:100%;animation:tick 40s linear infinite;}
@keyframes tick{to{transform:translateX(-100%);}}
@media (prefers-reduced-motion:reduce){.ticker-track{animation:none;padding-left:1rem;white-space:normal;}}
.st-key-sos_main button,.st-key-sos_side button{background:#C0392B !important;border:0 !important;border-radius:12px;padding:.7rem 1rem;box-shadow:0 2px 0 #8E2A20;}
.st-key-sos_main button:hover,.st-key-sos_side button:hover{background:#A93226 !important;}
.st-key-sos_main button *,.st-key-sos_side button *{color:#fff !important;font-weight:700;}
.sos-note{color:var(--muted);font-size:.9rem;}
.alert-banner small.sms{margin-top:.4rem;background:rgba(0,0,0,.28);padding:.3rem .55rem;border-radius:6px;opacity:1;font-size:.8rem;}
.fc-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(88px,1fr));gap:.5rem;margin:.4rem 0 .7rem;}
.fc-day{border:1px solid var(--card-line);border-top:6px solid var(--c);border-radius:12px;background:var(--card-bg);padding:.55rem .4rem .5rem;text-align:center;font-size:.78rem;line-height:1.35;color:inherit;}
.fc-d{font-weight:700;font-size:.86rem;}
.fc-date,.fc-sub{color:var(--muted);font-size:.74rem;}
.fc-ic{font-size:1.5rem;line-height:1.5;}
.fc-rain b{font-family:'Bricolage Grotesque',sans-serif;font-size:1.3rem;}
.fc-bar{height:6px;border-radius:3px;background:var(--card-line);margin:.45rem 0 .3rem;overflow:hidden;}
.fc-bar i{display:block;height:100%;background:var(--c);}
.fc-risk{font-weight:600;font-size:.74rem;}
.pred{display:flex;gap:.6rem;align-items:flex-start;background:var(--card-bg);border:1px solid var(--card-line);border-left:6px solid var(--c);border-radius:10px;padding:.5rem .7rem;margin:.35rem 0;font-size:.88rem;color:inherit;}
.pred .lv{margin-left:auto;font-size:.7rem;font-weight:700;white-space:nowrap;padding:.05rem .45rem;border:1px solid var(--card-line);border-radius:6px;}
@media (max-width:640px){.hero{padding:1.2rem;}.hero h1{font-size:1.6rem;}.page-title{font-size:1.6rem;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def h(s: str) -> str:
    """Flatten HTML so Markdown never treats indented lines as code."""
    return "".join(line.strip() for line in s.splitlines())


def esc(x) -> str:
    return _html.escape(str(x))


# ───────────────────────────── State helpers ─────────────────────────────
STORE = st.session_state.setdefault("_store", {})


def persist(fn, label, key, default, **kw):
    """Widget whose value survives page switches (Streamlit drops unrendered widget state)."""
    if key not in st.session_state:
        st.session_state[key] = STORE.get(key, default)
    val = fn(label, key=key, **kw)
    STORE[key] = val
    return val


DEFAULTS = dict(
    p_name="Demo Farm", p_village="Orathanadu", p_district="Thanjavur", p_state="Tamil Nadu",
    p_lat=10.7870, p_lon=79.1378, p_acres=3.5, p_crop="Paddy", p_soil="Alluvial",
    p_irrigation="Canal", p_ownership="Owner", p_social="General", p_loan=True, p_insured=False,
    p_phone="", p_lang="English", s_basemap="Satellite", s_refresh=10, s_notify_min="Warning", s_offline=False, n_sms=True, n_push=True, n_voice=False,
    s_layer="NDVI vegetation health", p_survey="", p_survey_skip=False, p_survey_input="",
    s_provider="Open-Meteo (no key)", s_owm_key="", s_auto=True, s_gust=60, s_rain_h=2.5,
    s_rain_hrs=3, s_rain_24=100.0, s_dry=14, s_hum=80,
)


def P(key):
    return STORE.get(key, DEFAULTS[key])


def farm_class(acres: float) -> str:
    ha = acres / 2.471
    if ha < 1: return "Marginal"
    if ha < 2: return "Small"
    if ha < 4: return "Semi-medium"
    if ha < 10: return "Medium"
    return "Large"


# ───────────────────────────── Domain data ─────────────────────────────
CROPS = ["Paddy", "Groundnut", "Sugarcane", "Banana", "Tomato", "Maize", "Ragi", "Cotton"]
REV_PER_ACRE = {"Paddy": 55000, "Groundnut": 48000, "Sugarcane": 120000, "Banana": 180000,
                "Tomato": 150000, "Maize": 42000, "Ragi": 36000, "Cotton": 60000}
VULN = {  # crop sensitivity multiplier per hazard
    "Paddy": dict(Drought=1.1, Flood=.8, Cyclone=1.0, Pest=1.0, Wind=.9),
    "Groundnut": dict(Drought=1.2, Flood=1.1, Cyclone=.9, Pest=1.0, Wind=.7),
    "Sugarcane": dict(Drought=1.0, Flood=.7, Cyclone=1.0, Pest=.9, Wind=.8),
    "Banana": dict(Drought=.9, Flood=1.0, Cyclone=1.3, Pest=.9, Wind=1.3),
    "Tomato": dict(Drought=1.0, Flood=1.3, Cyclone=1.1, Pest=1.2, Wind=.9),
    "Maize": dict(Drought=1.0, Flood=1.0, Cyclone=1.0, Pest=.9, Wind=1.1),
    "Ragi": dict(Drought=.7, Flood=1.0, Cyclone=.9, Pest=.8, Wind=.7),
    "Cotton": dict(Drought=.9, Flood=1.2, Cyclone=1.0, Pest=1.3, Wind=.9),
}
HK = {"Drought": "Drought", "Flood": "Flood", "Cyclone": "Cyclone", "Pest Outbreak": "Pest", "High Winds": "Wind"}

HAZARDS = {"Drought": dict(icon="☀️"), "Flood": dict(icon="🌊"), "Cyclone": dict(icon="🌀"),
           "Pest Outbreak": dict(icon="🐛"), "High Winds": dict(icon="💨")}

LEVELS = [(25, "Low", "#5FA36B"), (50, "Moderate", "#E8A33D"), (75, "High", "#EA7A3A"), (101, "Severe", "#D64933")]


def level_of(score):
    for cap, name, col in LEVELS:
        if score < cap:
            return name, col
    return LEVELS[-1][1], LEVELS[-1][2]


def tag_of_idx(idx):
    """Risk index to warning tier. 25 to 49 is a watch, 50 to 74 a warning, 75 and above an alert."""
    return "ALERT" if idx >= 75 else "WARNING" if idx >= 50 else "WATCH" if idx >= 25 else None


def compute(hz, idx):
    """Crop impact for a hazard at a given 0 to 100 risk index. Nothing is lost below the watch level."""
    crop, acres = P("p_crop"), P("p_acres")
    hit = idx >= 25
    loss_pct = min(95.0, idx * VULN[crop][HK[hz]] * 0.7) if hit else 0.0
    area_frac = min(1.0, 0.25 + 0.7 * idx / 100) if hit else 0.0
    loss = acres * area_frac * REV_PER_ACRE[crop] * loss_pct / 100
    name, col = level_of(idx)
    return dict(hz=hz, idx=idx, level=name, color=col, loss_pct=loss_pct, area=acres * area_frac, loss=loss)


# ───────────────────────────── Map ─────────────────────────────
FARM_UNIT = [(-0.95, -0.55), (-0.7, 0.75), (0.1, 1.0), (0.9, 0.6), (1.0, -0.4), (0.35, -0.95), (-0.5, -0.9)]
ZONES = {  # name, cx, cy, rx, ry, weight (1 = most exposed)
    "Drought": [("Ridge plots, highest moisture deficit", .35, .45, .55, .45, 1.0), ("Sandy patch, east boundary", .7, -.3, .35, .4, .85), ("Central plots", -.1, 0, .5, .4, .6)],
    "Flood": [("Low-lying strip along the stream", -.4, -.6, .9, .28, 1.0), ("Depression, north-west", -.6, .5, .4, .35, .7), ("Field drain junction", .5, -.7, .3, .25, .8)],
    "Cyclone": [("Windward west edge", -.75, 0, .4, .9, 1.0), ("Open central field", 0, .1, .6, .7, .75), ("Sheltered east side", .7, .2, .3, .6, .45)],
    "Pest Outbreak": [("Hotspot A", -.4, .4, .28, .28, 1.0), ("Hotspot B", .35, .55, .25, .25, .85), ("Hotspot C", .1, -.4, .3, .3, .7), ("Edge infestation", .75, -.4, .2, .2, .5)],
    "High Winds": [("Exposed north edge", 0, .8, .9, .3, 1.0), ("Open west side", -.7, .1, .35, .7, .8), ("Tall-crop block", .4, 0, .4, .5, .6)],
}
ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
S2_CLOUDLESS = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/{z}/{y}/{x}.jpg"
BASEMAPS = ["Satellite", "Sentinel-2 cloudless", "Street map"]
LAYERS = ["NDVI vegetation health", "Hazard zones", "Both"]


def shoelace(pts):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2


# ───────────────────────────── RTC / Survey number database ─────────────────────────────
# Sample records. Each polygon is a list of (latitude, longitude) vertices in WGS84.
# In production this lookup would call a state land-records service (for example Bhoomi RTC or Tamil Nadu Patta/Chitta).
SURVEYS = {
    "SURVEY_101": dict(owner="Murugesan", village="Orathanadu", taluk="Orathanadu", district="Thanjavur", state="Tamil Nadu",
                       crop="Paddy", soil="Alluvial", irrigation="Canal",
                       polygon=[(10.786656, 79.137196), (10.787469, 79.137355), (10.787625, 79.137864), (10.787375, 79.138373),
                                (10.78675, 79.138436), (10.786406, 79.138023), (10.786438, 79.137482)]),
    "SURVEY_102": dict(owner="Lakshmi", village="Swamimalai", taluk="Kumbakonam", district="Thanjavur", state="Tamil Nadu",
                       crop="Banana", soil="Alluvial", irrigation="Canal",
                       polygon=[(10.932695, 79.369482), (10.933356, 79.369534), (10.933483, 79.370104), (10.933254, 79.370518),
                                (10.932593, 79.370414)]),
    "SURVEY_103": dict(owner="Selvam", village="Melur", taluk="Melur", district="Madurai", state="Tamil Nadu",
                       crop="Cotton", soil="Black cotton", irrigation="Borewell",
                       polygon=[(10.028696, 78.340229), (10.029683, 78.340537), (10.029607, 78.34154), (10.028924, 78.341771),
                                (10.028317, 78.341463), (10.028393, 78.340692)]),
    "SURVEY_104": dict(owner="Kavitha", village="Kinathukadavu", taluk="Pollachi", district="Coimbatore", state="Tamil Nadu",
                       crop="Tomato", soil="Red loam", irrigation="Drip",
                       polygon=[(10.641616, 77.020609), (10.642213, 77.020587), (10.642427, 77.021), (10.642128, 77.021413),
                                (10.641637, 77.021347)]),
    "SURVEY_105": dict(owner="Ramasamy", village="Nannilam", taluk="Nannilam", district="Tiruvarur", state="Tamil Nadu",
                       crop="Sugarcane", soil="Alluvial", irrigation="Borewell",
                       polygon=[(10.744764, 79.609199), (10.74563, 79.609359), (10.745787, 79.61024), (10.745551, 79.610801),
                                (10.744606, 79.610761), (10.744213, 79.61016), (10.744331, 79.609519)]),
}
SURVEY_NOT_FOUND = "Survey number not found. Please try a sample ID like SURVEY_101"


def normalise_survey(raw) -> str:
    """'survey 101', 'Survey-101', 'RTC 101' and '101' all become 'SURVEY_101'."""
    s = re.sub(r"[\s\-/]+", "_", str(raw or "").strip().upper()[:60]).strip("_")
    if s.startswith("RTC_"):
        s = s[4:]
    if s.startswith("SURVEY") and not s.startswith("SURVEY_"):
        s = "SURVEY_" + s[6:]
    if s.isdigit():
        s = "SURVEY_" + s
    return s


def lookup_survey(raw):
    """Return (record, None) on success or (None, message) on failure. Never raises."""
    try:
        key = normalise_survey(raw)
        if not key:
            return None, "Enter your RTC or survey number first, for example SURVEY_101."
        rec = SURVEYS.get(key)
        if rec is None:
            return None, SURVEY_NOT_FOUND
        return dict(rec, id=key), None
    except Exception:
        return None, SURVEY_NOT_FOUND


def polygon_bbox_centre(poly):
    lats, lons = [p[0] for p in poly], [p[1] for p in poly]
    return (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2


def polygon_acres(poly):
    lat0, lon0 = polygon_bbox_centre(poly)
    kx = 111320.0 * math.cos(math.radians(lat0))
    return shoelace([((lo - lon0) * kx, (la - lat0) * 111320.0) for la, lo in poly]) / 4046.86


def farm_geometry():
    """Farm boundary as lat/lon vertices plus a local frame: centre (lat, lon) and half-extents hx, hy in metres.
    Uses the linked survey polygon when there is one, otherwise a shape generated from farm size."""
    rec = SURVEYS.get(P("p_survey"))
    if rec:
        poly = [list(p) for p in rec["polygon"]]
        clat, clon = polygon_bbox_centre(poly)
        kx = 111320.0 * math.cos(math.radians(clat))
        hx = (max(p[1] for p in poly) - min(p[1] for p in poly)) / 2 * kx
        hy = (max(p[0] for p in poly) - min(p[0] for p in poly)) / 2 * 111320.0
        return dict(poly=poly, lat=clat, lon=clon, hx=hx, hy=hy, survey=P("p_survey"))
    lat0, lon0, acres = P("p_lat"), P("p_lon"), P("p_acres")
    k = math.sqrt(acres * 4046.86 / shoelace(FARM_UNIT))
    g = dict(lat=lat0, lon=lon0, hx=k, hy=k, survey="")
    g["poly"] = [to_ll(g, x, y) for x, y in FARM_UNIT]
    return g


def to_ll(g, x, y):
    """Unit coordinates (-1..1 across the farm) to [lat, lon]."""
    return [g["lat"] + y * g["hy"] / 111320.0,
            g["lon"] + x * g["hx"] / (111320.0 * math.cos(math.radians(g["lat"])))]


def _inside(x, y, poly):
    """Ray-casting point-in-polygon test. poly is a list of (x, y)."""
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


# ───────────────────────────── Simulated NDVI ─────────────────────────────
NDVI_BASE = {"Paddy": .72, "Groundnut": .62, "Sugarcane": .78, "Banana": .75, "Tomato": .60, "Maize": .70, "Ragi": .58, "Cotton": .60}
NDVI_CLASSES = [(0.60, "Healthy", "#2E9E4F"), (0.45, "Watch", "#F2C200"), (0.30, "Stressed", "#EA7A3A"), (-1.0, "Critical", "#D64933")]
NDVI_RANGE = {"Healthy": "0.60 and above", "Watch": "0.45 to 0.60", "Stressed": "0.30 to 0.45", "Critical": "below 0.30"}


def ndvi_class(v):
    for lo, name, col in NDVI_CLASSES:
        if v >= lo:
            return name, col
    return NDVI_CLASSES[-1][1], NDVI_CLASSES[-1][2]


def ndvi_field(g, S, cells_across=16):
    """Simulated NDVI on a grid clipped to the farm polygon.
    Healthy crop sits near the crop's base NDVI. The hazard scenario pulls NDVI down inside the
    exposed zones, so the map reacts to the live forecast. A survey-seeded soft noise field adds
    realistic patchiness that stays the same between reruns."""
    lat0, lon0 = g["lat"], g["lon"]
    kx, ky = 111320.0 * math.cos(math.radians(lat0)), 111320.0
    pts = [((lo - lon0) * kx, (la - lat0) * ky) for la, lo in g["poly"]]
    w, hgt = 2 * g["hx"], 2 * g["hy"]
    cell = max(w, hgt) / cells_across
    nx, ny = max(1, math.ceil(w / cell)), max(1, math.ceil(hgt / cell))
    x0, y0 = -g["hx"], -g["hy"]
    rng = np.random.default_rng(zlib.crc32(f"{g['survey'] or 'demo'}|{P('p_crop')}".encode()))
    blobs = [(rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(.3, .7), rng.uniform(-.08, .08)) for _ in range(4)]
    base = NDVI_BASE.get(P("p_crop"), .65)
    load = S["idx"] / 100
    scale = 0.35 + 0.65 * load
    out = []
    for i in range(nx):
        for j in range(ny):
            cx, cy = x0 + (i + .5) * cell, y0 + (j + .5) * cell
            if not _inside(cx, cy, pts):
                continue
            ux, uy = cx / g["hx"], cy / g["hy"]
            stress = max(wt * math.exp(-(((ux - zx) / (rx * scale)) ** 2 + ((uy - zy) / (ry * scale)) ** 2))
                         for _, zx, zy, rx, ry, wt in ZONES[S["hz"]])
            patch = sum(a * math.exp(-(((ux - bx) / r) ** 2 + ((uy - by) / r) ** 2)) for bx, by, r, a in blobs)
            v = base - base * 0.9 * load * stress - 0.10 * load + patch + rng.normal(0, 0.015)
            v = float(min(0.90, max(0.05, v)))
            name, col = ndvi_class(v)
            out.append(dict(ndvi=v, cls=name, color=col,
                            bounds=[[lat0 + (cy - cell / 2) / ky, lon0 + (cx - cell / 2) / kx],
                                    [lat0 + (cy + cell / 2) / ky, lon0 + (cx + cell / 2) / kx]]))
    vals = [c["ndvi"] for c in out]
    n = max(1, len(out))
    share = {name: sum(c["cls"] == name for c in out) / n * 100 for _, name, _ in NDVI_CLASSES}
    return dict(cells=out, mean=float(np.mean(vals)) if vals else 0.0, share=share)


def build_map(S, g=None, nd=None):
    g = g or farm_geometry()
    nd = nd or ndvi_field(g, S)
    lat0, lon0, acres = g["lat"], g["lon"], P("p_acres")
    basemap, layer = P("s_basemap"), P("s_layer")

    m = folium.Map(location=[lat0, lon0], zoom_start=17, tiles=None, control_scale=True)
    folium.TileLayer(ESRI, attr="Imagery © Esri, Maxar, Earthstar Geographics", name="Satellite (Esri)",
                     show=basemap == "Satellite", max_zoom=19).add_to(m)
    folium.TileLayer(S2_CLOUDLESS, attr="Sentinel-2 cloudless by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2020)",
                     name="Sentinel-2 cloudless", show=basemap.startswith("Sentinel"), max_zoom=19, max_native_zoom=13).add_to(m)
    folium.TileLayer("OpenStreetMap", name="Street map", show=basemap == "Street map").add_to(m)

    ndvi_layer = folium.FeatureGroup(name="NDVI vegetation health (simulated)", show=layer in ("NDVI vegetation health", "Both")).add_to(m)
    for c in nd["cells"]:
        folium.Rectangle(c["bounds"], color=c["color"], weight=0, fill=True, fill_color=c["color"],
                         fill_opacity=0.62, tooltip=f"NDVI {c['ndvi']:.2f}: {c['cls']}").add_to(ndvi_layer)

    zones = folium.FeatureGroup(name="Hazard zones", show=layer in ("Hazard zones", "Both")).add_to(m)
    scale = 0.35 + 0.65 * S["idx"] / 100
    for name, cx, cy, rx, ry, w in ZONES[S["hz"]]:
        pts = [to_ll(g, cx + rx * scale * math.cos(a), cy + ry * scale * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 30)]
        lvl, col = level_of(S["idx"] * w)
        folium.Polygon(pts, color=col, weight=1.5, fill=True, fill_color=col, fill_opacity=0.25 + 0.4 * S["idx"] / 100,
                       tooltip=f"{name}: {lvl} risk").add_to(zones)

    label = f"{esc(P('p_name'))}: {acres:g} acres of {esc(P('p_crop'))}" + (f" ({g['survey']})" if g["survey"] else "")
    folium.Polygon(g["poly"], color="#C6F36B", weight=3, fill=True, fill_color="#C6F36B", fill_opacity=0.04, tooltip=label).add_to(m)
    if g["survey"]:
        water = [sum(p[0] for p in g["poly"]) / len(g["poly"]), sum(p[1] for p in g["poly"]) / len(g["poly"])]
        gate = g["poly"][0]
    else:
        water, gate = to_ll(g, 0.2, -0.1), to_ll(g, -0.8, -0.7)
    folium.Marker(water, tooltip="Water source", icon=folium.Icon(color="blue", icon="tint", prefix="fa")).add_to(m)
    folium.Marker(gate, tooltip="Farm gate", icon=folium.Icon(color="green", icon="home", prefix="fa")).add_to(m)
    lats, lons = [p[0] for p in g["poly"]], [p[1] for p in g["poly"]]
    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(30, 30))
    folium.LayerControl(collapsed=True).add_to(m)
    return m


# ───────────────────────────── Live 5-day forecast + early warning engine ─────────────────────────────
PROVIDERS = ["Open-Meteo (no key)", "OpenWeatherMap", "Demo storm (offline)"]
FORECAST_DAYS = 5


def _max_run(vals, thr):
    best = cur = 0
    for v in vals:
        cur = cur + 1 if (v or 0) >= thr else 0
        best = max(best, cur)
    return best


def _n(v, default=0.0):
    return default if v is None else float(v)


def aggregate_days(rows, today):
    """Hourly rows (local time at the farm) to one summary per calendar day."""
    out = []
    for i in range(FORECAST_DAYS):
        d = today + timedelta(days=i)
        r = [x for x in rows if x["t"].date() == d]
        if not r:
            continue
        temps = [x["temp"] for x in r if x["temp"] is not None] or [25.0]
        hums = [x["hum"] for x in r if x["hum"] is not None] or [60.0]
        pops = [x["pop"] for x in r if x["pop"] is not None]
        out.append(dict(date=d, rain=sum(x["rain"] for x in r), rain_series=[x["rain"] for x in r],
                        gust=max(x["gust"] for x in r), wind=max(x["wind"] for x in r),
                        tmax=max(temps), tmin=min(temps), tmean=sum(temps) / len(temps),
                        hum=sum(hums) / len(hums), pop=max(pops) if pops else None))
    return out


def _openmeteo_forecast(lat, lon):
    r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=8, params=dict(
        latitude=lat, longitude=lon, wind_speed_unit="kmh", timezone="auto", past_days=25, forecast_days=FORECAST_DAYS,
        current="temperature_2m,relative_humidity_2m,wind_speed_10m,wind_gusts_10m,precipitation",
        hourly="temperature_2m,relative_humidity_2m,precipitation,precipitation_probability,wind_speed_10m,wind_gusts_10m",
        daily="precipitation_sum"))
    r.raise_for_status()
    j = r.json()
    cur, hh, dd = j["current"], j["hourly"], j["daily"]
    now_t = datetime.fromisoformat(cur["time"])
    today = now_t.date()
    times = hh["time"]

    def col(name):
        return hh.get(name) or [None] * len(times)

    rain, gust, wind = col("precipitation"), col("wind_gusts_10m"), col("wind_speed_10m")
    temp, hum, pop = col("temperature_2m"), col("relative_humidity_2m"), col("precipitation_probability")
    rows = [dict(t=datetime.fromisoformat(t), rain=_n(rain[i]), gust=_n(gust[i]), wind=_n(wind[i]),
                 temp=temp[i], hum=hum[i], pop=pop[i]) for i, t in enumerate(times)]
    idx = max((i for i, x in enumerate(rows) if x["t"] <= now_t), default=0)
    dates, ps = dd["time"], [_n(v) for v in dd["precipitation_sum"]]
    di = dates.index(today.isoformat()) if today.isoformat() in dates else max(0, len(dates) - FORECAST_DAYS)
    dry_before = 0  # consecutive dry days (under 1 mm) before today
    for v in reversed(ps[:di]):
        if v >= 1.0:
            break
        dry_before += 1
    pr = [x["rain"] for x in rows]
    now = dict(temp=_n(cur.get("temperature_2m")), humidity=_n(cur.get("relative_humidity_2m")), wind=_n(cur.get("wind_speed_10m")),
               gust=_n(cur.get("wind_gusts_10m")), rain_now=_n(cur.get("precipitation")),
               rain_past24=sum(pr[max(0, idx - 23):idx + 1]), rain_next24=sum(pr[idx + 1:idx + 25]))
    return dict(source="Open-Meteo", live=True, fetched_at=datetime.now(), today=today, now=now,
                days=aggregate_days(rows, today), dry_before=dry_before)


def _owm_forecast(lat, lon, key):
    """OpenWeatherMap free tier: current conditions plus the 5-day / 3-hour forecast (no rain history)."""
    base = dict(lat=lat, lon=lon, appid=key, units="metric")
    r = requests.get("https://api.openweathermap.org/data/2.5/weather", params=base, timeout=8)
    r.raise_for_status()
    c = r.json()
    r = requests.get("https://api.openweathermap.org/data/2.5/forecast", params=base, timeout=8)
    r.raise_for_status()
    f = r.json()
    steps = f.get("list", [])
    off = timedelta(seconds=(f.get("city") or {}).get("timezone", 0))
    rows = []
    for s in steps:  # each step covers the 3 hours ending at dt, so spread it over 3 hourly rows
        end = datetime.fromtimestamp(s["dt"], tz=timezone.utc).replace(tzinfo=None) + off
        rain3 = (s.get("rain") or {}).get("3h", 0.0)
        w = s["wind"]
        for k in (2, 1, 0):
            rows.append(dict(t=end - timedelta(hours=k), rain=rain3 / 3, gust=w.get("gust", w["speed"]) * 3.6,
                             wind=w["speed"] * 3.6, temp=s["main"]["temp"], hum=s["main"]["humidity"],
                             pop=round(s.get("pop", 0.0) * 100)))
    today = (datetime.fromtimestamp(c["dt"], tz=timezone.utc).replace(tzinfo=None) + timedelta(seconds=c.get("timezone", 0))).date()
    cw = c["wind"]
    now = dict(temp=c["main"]["temp"], humidity=c["main"]["humidity"], wind=cw["speed"] * 3.6,
               gust=cw.get("gust", cw["speed"]) * 3.6, rain_now=(c.get("rain") or {}).get("1h", 0.0),
               rain_past24=None, rain_next24=sum((s.get("rain") or {}).get("3h", 0.0) for s in steps[:8]))
    return dict(source="OpenWeatherMap", live=True, fetched_at=datetime.now(), today=today, now=now,
                days=aggregate_days(rows, today), dry_before=None)


@st.cache_data(ttl=600, show_spinner=False)
def fetch_forecast(provider, lat, lon, key):
    """Normalised 5-day forecast for the farm coordinates. Wind in km/h, rain in mm. Raises on failure."""
    if provider.startswith("OpenWeather"):
        return _owm_forecast(lat, lon, key)
    return _openmeteo_forecast(lat, lon)


# (rain mm, peak gust km/h, max wind km/h, max temp, min temp, humidity %, rain chance %)
DEMO_STORM = [(6, 38, 22, 31, 25, 80, 60), (48, 62, 44, 29, 25, 88, 85), (128, 96, 66, 27, 24, 94, 95),
              (72, 55, 36, 27, 24, 92, 90), (10, 34, 20, 29, 24, 84, 50)]
DEMO_CALM = [(0, 18, 10, 33, 25, 62, 5), (0, 20, 11, 34, 25, 60, 5), (2, 22, 12, 33, 25, 64, 15),
             (0, 17, 9, 34, 26, 58, 5), (0, 19, 10, 33, 25, 61, 10)]


def demo_forecast(storm):
    """Offline forecast. The storm has a cyclone and flood building over days 2 to 4; the calm one is a quiet week."""
    today = datetime.now().date()
    rows = []
    for i, (rain, gust, wind, tmax, tmin, hum, pop) in enumerate(DEMO_STORM if storm else DEMO_CALM):
        bell = [math.exp(-(((hr - 15) / 3.5) ** 2)) for hr in range(24)]
        tot = sum(bell)
        for hr in range(24):
            b = bell[hr]
            rows.append(dict(t=datetime.combine(today + timedelta(days=i), datetime.min.time()) + timedelta(hours=hr),
                             rain=rain * b / tot, gust=gust * (0.55 + 0.45 * b), wind=wind * (0.6 + 0.4 * b),
                             temp=tmin + (tmax - tmin) * math.exp(-(((hr - 14) / 5) ** 2)), hum=hum, pop=pop))
    now = (dict(temp=28.0, humidity=90, wind=30.0, gust=48.0, rain_now=3.0, rain_past24=22.0, rain_next24=60.0) if storm else
           dict(temp=31.0, humidity=62, wind=10.0, gust=18.0, rain_now=0.0, rain_past24=0.0, rain_next24=0.5))
    return dict(source="Demo storm (offline)" if storm else "Offline sample", live=False, fetched_at=datetime.now(),
                today=today, now=now, days=aggregate_days(rows, today), dry_before=0 if storm else 4)


def _trim_stale(fc):
    """A saved forecast may be days old. Drop days that have passed and carry the dry-spell count forward."""
    t = datetime.now().date()
    if fc["today"] >= t:
        return fc
    fc = dict(fc)
    if fc.get("dry_before") is not None:
        run = fc["dry_before"]
        for d in fc["days"]:
            if d["date"] >= t:
                break
            run = run + 1 if d["rain"] < 1.0 else 0
        fc["dry_before"] = run
    fc["days"] = [d for d in fc["days"] if d["date"] >= t]
    fc["today"] = t
    if not fc["days"]:
        fc["unavailable"] = True
    return fc


def _fallback(ss, prov, msg):
    snap = ss.get("_wx_snap")
    if snap:
        fc = _trim_stale(dict(snap["w"])); fc["source"] = f"Cached copy from {snap['at']:%H:%M}"; fc["live"] = False
        return fc, f"Could not reach {prov} ({msg[:120]}). Showing your last synced forecast."
    fc = demo_forecast(False); fc["unavailable"] = True  # sample numbers, never treated as an all-clear
    return fc, f"Could not fetch from {prov}: {msg[:160]}. Live warnings are paused until the forecast loads."


def refresh_forecast():
    fetch_forecast.clear()
    st.session_state.pop("_fc_fail", None)


def get_forecast():
    """Returns (forecast, error_or_None). Never raises. Falls back to the cached forecast, then to clearly marked sample data."""
    ss, prov = st.session_state, P("s_provider")
    if P("s_offline"):
        snap = ss.get("_wx_snap")
        if snap:
            fc = _trim_stale(dict(snap["w"])); fc["source"] = f"Offline cache, synced {snap['at']:%d %b %H:%M}"; fc["live"] = False
            return fc, None
        fc = demo_forecast(False); fc["unavailable"] = True
        return fc, "Offline mode is on and no forecast has been saved yet. Press Sync now in Settings."
    if prov.startswith("Demo"):
        fc = demo_forecast(True)
        ss["_wx_snap"] = dict(w=dict(fc), at=fc["fetched_at"])
        return fc, None
    key = P("s_owm_key") or os.environ.get("OPENWEATHER_API_KEY", "")
    args = (prov, round(P("p_lat"), 4), round(P("p_lon"), 4), key)
    fail = ss.get("_fc_fail")  # after a failure, do not hit the network again for a minute (many parts of a page ask for the forecast)
    if fail and fail[0] == args and (datetime.now() - fail[1]).total_seconds() < 60:
        return _fallback(ss, prov, fail[2])
    try:
        if prov.startswith("OpenWeather") and not key:
            raise ValueError("no API key. Add one in Settings under Weather and alert rules")
        fc = fetch_forecast(*args)
        ss["_wx_snap"] = dict(w=dict(fc), at=fc["fetched_at"])
        ss.pop("_fc_fail", None)
        return fc, None
    except Exception as e:  # network, quota, bad key, parsing
        msg = str(e).replace(key, "***") if key else str(e)
        ss["_fc_fail"] = (args, datetime.now(), msg)
        return _fallback(ss, prov, msg)


# ── day helpers ──
def dpart(d):
    return f"{d:%a} {d.day} {d:%b}"


def rel_day(n):
    return "today" if n == 0 else "tomorrow" if n == 1 else f"in {n} days" if n > 1 else f"{-n} days ago"


def when_phrase(d, today):
    return f"on {dpart(d)} ({rel_day((d - today).days)})"


def day_label(d, today):
    n = (d - today).days
    return "Today" if n == 0 else "Tomorrow" if n == 1 else f"{d:%a}"


def day_icon(d):
    if d["gust"] > P("s_gust"): return "🌀"
    if d["rain"] >= 50: return "⛈️"
    if d["rain"] >= 10: return "🌧️"
    if d["rain"] >= 1: return "🌦️"
    return "☀️" if d["hum"] < 75 else "⛅"


# ── thresholds: a watch starts at 65% of a warning threshold, an alert at 150% ──
def band(v, warn):
    if v is None: return None
    if v >= 1.5 * warn: return "ALERT"
    if v > warn: return "WARNING"
    if v >= 0.65 * warn: return "WATCH"
    return None


def band_idx(v, warn):
    """0 to 100 risk score that always lands in the same tier as band(): watch 25-49, warning 50-74, alert 75+."""
    if v is None: return 0.0
    if v < 0.65 * warn: return 24.0 * v / (0.65 * warn)
    if v <= warn: return 25.0 + 24.0 * (v - 0.65 * warn) / (0.35 * warn)
    if v < 1.5 * warn: return 50.0 + 24.0 * (v - warn) / (0.5 * warn)
    return min(100.0, 75.0 + 25.0 * (v - 1.5 * warn) / (0.6 * warn))


def daily_series(fc):
    """Per-day quantities the rules look at."""
    days, rain_h, hum_t = fc["days"], P("s_rain_h"), P("s_hum")
    dry = None
    if fc.get("dry_before") is not None:  # projected dry spell: days already dry plus dry days still to come
        run, dry = fc["dry_before"], []
        for d in days:
            run = run + 1 if d["rain"] < 1.0 else 0
            dry.append(run)
    pest, run = [], 0
    for d in days:
        run = run + 1 if (d["hum"] >= hum_t and 25 <= d["tmean"] <= 33) else 0
        pest.append(run)
    return dict(gust=[d["gust"] for d in days], rain=[d["rain"] for d in days],
                heavy=[_max_run(d["rain_series"], rain_h) for d in days], dry=dry, pest=pest)


def hazard_curves(fc):
    """For every hazard: a 0-100 risk index for each forecast day, plus short and long descriptions."""
    ser = daily_series(fc)
    gust_t, rain_t, dry_t, hrs = float(P("s_gust")), float(P("s_rain_24")), float(P("s_dry")), int(P("s_rain_hrs"))
    cv = {hz: dict(idx=[], short=[], num=[], clause=[]) for hz in HAZARDS}

    def put(hz, idx, short, num, clause):
        c = cv[hz]
        c["idx"].append(float(idx)); c["short"].append(short); c["num"].append(num); c["clause"].append(clause)

    for i in range(len(fc["days"])):
        g, r, hv = ser["gust"][i], ser["rain"][i], ser["heavy"][i]
        gtxt, bi = f"Gusts up to {g:.0f} km/h", band_idx(g, gust_t)
        extra = f", with {hv} hours of heavy downpour" if hv >= hrs else ""
        put("Flood", max(band_idx(r, rain_t), 30.0 if hv >= hrs else 0.0), f"About {r:.0f} mm of rain expected",
            f"{r:.0f} mm", f"About {r:.0f} mm of rain is forecast {{when}}{extra}.")
        put("Cyclone", bi if g > gust_t else min(24.0, bi), gtxt, f"{g:.0f} km/h", f"{gtxt} are forecast {{when}}.")
        put("High Winds", bi if g <= gust_t else 0.0, gtxt, f"{g:.0f} km/h", f"{gtxt} are forecast {{when}}.")
        if ser["dry"] is None:
            put("Drought", 0.0, "", "", "")
        else:
            run = ser["dry"][i]
            put("Drought", band_idx(run, dry_t), f"{run} dry days in a row", f"{run} days",
                f"The dry spell is forecast to reach {run} days {{when}}, after {fc['dry_before']} dry days so far.")
        p = ser["pest"][i]
        put("Pest Outbreak", 30.0 + min(19.0, 5.0 * (p - 2)) if p >= 2 else (20.0 if p == 1 else 0.0),
            f"Warm, humid spell of {p} days", f"{p} days", f"Warm, humid weather is forecast for {p} days in a row, ending {{when}}.")
    return cv


def forecast_risks(fc):
    """Risk summary per hazard: peak risk index over the forecast window, when it peaks, and the crop impact."""
    out = {}
    for hz, c in hazard_curves(fc).items():
        if c["idx"]:
            k = max(range(len(c["idx"])), key=lambda i: c["idx"][i])  # earliest peak wins a tie
            idx, day = int(min(100.0, c["idx"][k])), fc["days"][k]["date"]
        else:
            k, idx, day = 0, 0, fc["today"]
        S = compute(hz, idx)
        S.update(k=k, day=day, lead=(day - fc["today"]).days, tag=tag_of_idx(idx), curve=[int(min(100.0, v)) for v in c["idx"]],
                 short=c["short"][k] if c["idx"] else "", num=c["num"][k] if c["idx"] else "", clause=c["clause"][k] if c["idx"] else "")
        out[hz] = S
    return out


def sim(hz=None):
    """Live risk for one hazard, or for the hazard with the highest predicted risk when hz is None."""
    risks = forecast_risks(get_forecast()[0])
    return risks[hz or max(risks, key=lambda x: risks[x]["idx"])]


def predicted_hazards():
    return [hz for hz, S in forecast_risks(get_forecast()[0]).items() if S["idx"] >= 25]


TITLES = {"Flood": dict(WATCH="Predicted flood risk", WARNING="Flood warning", ALERT="Severe flood alert"),
          "Cyclone": dict(WATCH="Predicted cyclone risk", WARNING="Cyclone warning", ALERT="Severe cyclone alert"),
          "High Winds": dict(WATCH="Predicted high winds", WARNING="High wind warning", ALERT="Severe wind alert"),
          "Drought": dict(WATCH="Predicted dry spell", WARNING="Drought warning", ALERT="Severe drought alert"),
          "Pest Outbreak": dict(WATCH="Predicted pest risk", WARNING="Pest warning", ALERT="Pest alert")}
ADVICE_LINE = {
    "Flood": "Clear field drains, move seed, fertiliser and pumps to higher ground, and photograph plots for insurance.",
    "Cyclone": "Harvest mature crop, stake tall plants and secure pumps, sheds and livestock.",
    "High Winds": "Stake tall crops such as banana, maize and sugarcane, and delay spraying.",
    "Drought": "Irrigate early in the morning and mulch to hold soil moisture.",
    "Pest Outbreak": "Scout your field every 2 days and set pheromone traps."}


def rule_rows(fc):
    """One row per alert rule: what the threshold is and the worst value in the forecast."""
    ser, days, today = daily_series(fc), fc["days"], fc["today"]
    gust_t, rain_t, dry_t, hum_t = P("s_gust"), P("s_rain_24"), P("s_dry"), P("s_hum")
    rain_h, hrs = P("s_rain_h"), int(P("s_rain_hrs"))
    rows = []

    def add(hz, rule, thr, vals, unit, status):
        k = max(range(len(vals)), key=lambda i: vals[i])
        st_txt = status.title() if status in RANK else (status or "Clear")
        rows.append({"Hazard": hz, "Rule": rule, "Threshold": thr, "Worst forecast": f"{vals[k]:.0f} {unit} on {dpart(days[k]['date'])}",
                     "Status": st_txt})

    g = ser["gust"]
    add("Cyclone", "Wind gusts", f"> {gust_t:g} km/h (alert at {1.5 * gust_t:.0f})", g, "km/h",
        band(max(g), gust_t) if band(max(g), gust_t) in ("WARNING", "ALERT") else None)
    add("High Winds", "Strong gusts", f"{0.65 * gust_t:.0f} to {gust_t:g} km/h", g, "km/h",
        "WATCH" if any(band(x, gust_t) == "WATCH" for x in g) else None)
    add("Flood", "Rain in one day", f"> {rain_t:g} mm (watch at {0.65 * rain_t:.0f}, alert at {1.5 * rain_t:.0f})", ser["rain"], "mm",
        band(max(ser["rain"]), rain_t))
    add("Flood", "Continuous heavy rain", f"{hrs}+ h in a row at ≥ {rain_h:g} mm/h", ser["heavy"], "h in a row",
        "WATCH" if max(ser["heavy"]) >= hrs else None)
    if ser["dry"] is None:
        add("Drought", "Consecutive dry days", f"> {dry_t} days", [0], "days", "n/a")
        rows[-1]["Worst forecast"] = "needs rain history (Open-Meteo)"
    else:
        add("Drought", "Consecutive dry days", f"> {dry_t} days (watch at {0.65 * dry_t:.0f}, alert at {1.5 * dry_t:.0f})",
            ser["dry"], "days", band(max(ser["dry"]), dry_t))
    add("Pest Outbreak", "Warm and humid", f"humidity ≥ {hum_t}% and 25 to 33 °C for 2+ days", ser["pest"], "days in a row",
        "WATCH" if max(ser["pest"]) >= 2 else None)
    return rows


def evaluate_forecast(fc):
    """The early warning check. Compares the forecast with every threshold and returns (warnings, rule_status_rows).
    Each warning is the peak day for one hazard, with a plain-language message and the data for an SMS."""
    if not fc.get("days") or fc.get("unavailable"):
        return [], []
    warns = []
    for hz, S in forecast_risks(fc).items():
        if not S["tag"]:
            continue
        when = when_phrase(S["day"], fc["today"])
        warns.append(dict(id=hz, hazard=hz, tag=S["tag"], idx=S["idx"], day=S["day"], lead=S["lead"], when=when,
                          title=TITLES[hz][S["tag"]], text=f"{S['clause'].format(when=when)} {ADVICE_LINE[hz]}",
                          short=S["short"], num=S["num"]))
    warns.sort(key=lambda a: (-RANK[a["tag"]], a["day"], -a["idx"]))
    return warns, rule_rows(fc)


TAG_COLOR = {"ALERT": "#B3261E", "WARNING": "#B54708", "WATCH": "#8A5A00"}  # white text on these is 5.4:1 or better


def alert_banners(alerts, fc):
    if fc.get("unavailable"):
        st.warning("The live forecast is unavailable, so warnings could not be checked. Do not treat this as an all-clear. "
                   "Check IMD or your block office.")
        return
    if not alerts:
        st.markdown(f'<div class="clear-note">No warning thresholds crossed in the next {len(fc["days"])} days. '
                    f'Last check {fc["fetched_at"]:%H:%M} from {esc(fc["source"])}.</div>', unsafe_allow_html=True)
        return
    for a in alerts:
        sms = sms_text("alert", a["hazard"], a["tag"], a["lead"], a["short"], a["num"])
        sent = RANK[a["tag"]] >= MIN_RANK.get(P("s_notify_min"), 2)
        kind = "SMS alert" if sent else f"SMS preview, not sent because it is below your {P('s_notify_min')} level"
        st.markdown(h(f"""<div class="alert-banner" style="--c:{TAG_COLOR[a['tag']]}"><span class="ic">{HAZARDS[a['hazard']]['icon']}</span>
            <div><b>{esc(a['title'])}</b><small>{esc(a['text'])}</small><small class="sms">📱 {kind}: {esc(sms)}</small></div>
            <span class="tag">{a['tag']}</span></div>"""), unsafe_allow_html=True)


def weather_section():
    top, btn = st.columns([5, 1.2])
    top.subheader("Weather at your farm right now")
    btn.button("Refresh now", on_click=refresh_forecast, key="wx_refresh", **STRETCH)
    fc, err = get_forecast()
    if err:
        st.warning(err)
    n = fc["now"]
    c = st.columns(4)
    c[0].metric("Temperature", f"{n['temp']:.1f} °C")
    c[1].metric("Wind speed", f"{n['wind']:.0f} km/h")
    c[2].metric("Humidity", f"{n['humidity']:.0f}%")
    c[3].metric("Rain next 24 h", f"{n['rain_next24']:.0f} mm")
    past = "n/a" if n["rain_past24"] is None else f"{n['rain_past24']:.0f} mm"
    dry = "n/a" if fc["dry_before"] is None else f"{fc['dry_before']} days"
    kind = "Live" if fc["live"] else ("Sample" if fc.get("unavailable") else "Simulated")
    st.markdown(f'<div class="wx-src">{kind} data from {esc(fc["source"])} for {P("p_lat"):.3f}, {P("p_lon"):.3f}. '
                f'Updated {fc["fetched_at"]:%H:%M}. Gusts {n["gust"]:.0f} km/h. Rain past 24 h {past}. Dry days in a row before today {dry}.</div>',
                unsafe_allow_html=True)


def forecast_panel():
    """Live Weather Forecast & Risk Outlook: replaces the old what-if sliders."""
    fc, _ = get_forecast()
    st.subheader("Live Weather Forecast & Risk Outlook")
    days = fc["days"]
    if fc.get("unavailable") or not days:
        st.info("The live forecast is not available right now. Check your connection, then press Refresh now.")
        return
    risks, today = forecast_risks(fc), fc["today"]
    kind = "Live" if fc["live"] else "Simulated"
    st.caption(f"{kind} {len(days)}-day forecast from {fc['source']}, updated {fc['fetched_at']:%H:%M}. "
               "Risk is scored 0 to 100 against your alert thresholds.")
    cards = []
    for i, d in enumerate(days):
        top = max(risks, key=lambda hz: risks[hz]["curve"][i])
        idx = risks[top]["curve"][i]
        lvl, col = level_of(idx)
        chip = f"{top}: {lvl}" if idx >= 25 else "No hazard"
        pop = f'<div class="fc-sub">{d["pop"]:.0f}% chance</div>' if d.get("pop") is not None else ""
        cards.append(
            f'<div class="fc-day" style="--c:{col}"><div class="fc-d">{esc(day_label(d["date"], today))}</div>'
            f'<div class="fc-date">{d["date"].day} {d["date"]:%b}</div><div class="fc-ic">{day_icon(d)}</div>'
            f'<div class="fc-rain"><b>{d["rain"]:.0f}</b> mm</div>{pop}'
            f'<div class="fc-sub">Gusts {d["gust"]:.0f} km/h</div><div class="fc-sub">{d["tmax"]:.0f}° / {d["tmin"]:.0f}°C</div>'
            f'<div class="fc-bar"><i style="width:{max(4, idx)}%"></i></div><div class="fc-risk">{esc(chip)}</div></div>')
    st.markdown('<div class="fc-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    st.markdown("**Predicted hazards**")
    warns, _ = evaluate_forecast(fc)
    if not warns:
        st.markdown(f'<div class="clear-note">No hazards predicted for the next {len(days)} days.</div>', unsafe_allow_html=True)
    for a in warns:
        st.markdown(h(f'<div class="pred" style="--c:{TAG_COLOR[a["tag"]]}"><span>{HAZARDS[a["hazard"]]["icon"]}</span>'
                      f'<div><b>{esc(a["title"])}</b> {esc(a["when"])}<br><span class="fit">{esc(a["short"])}</span></div>'
                      f'<span class="lv">{a["tag"]}</span></div>'), unsafe_allow_html=True)
    with st.expander("Risk index by hazard and day"):
        st.dataframe(pd.DataFrame({day_label(d["date"], today): [risks[hz]["curve"][i] for hz in HAZARDS] for i, d in enumerate(days)},
                                  index=[f"{HAZARDS[hz]['icon']} {hz}" for hz in HAZARDS]), **STRETCH)
        st.caption("Below 25 is low, 25 to 49 a watch, 50 to 74 a warning and 75 or more an alert. Change thresholds in Settings.")


def rules_panel():
    fc, _ = get_forecast()
    alerts, checks = evaluate_forecast(fc)
    if not checks:
        st.info("Rules are checked once a live forecast is available.")
        return
    st.dataframe(pd.DataFrame(checks), hide_index=True, **STRETCH)
    st.caption(f"{len(alerts)} hazard(s) flagged. Change thresholds in Settings under Weather and alert rules."
               + ("" if P("s_auto") else " Automatic alerts are switched off."))


# ───────────────────────────── Notifications, dispatch, SOS ─────────────────────────────
L10N = {
    "English": dict(alert="SatCrop {tag}: {hz} risk near your farm {when}. {detail}. Open the app for steps.",
                    sos="SatCrop SOS from {name} at {lat:.4f}, {lon:.4f}. Please call back.",
                    test="SatCrop test message. Alerts are working.", hz={},
                    when={0: "today", 1: "tomorrow", "n": "in {n} days"}),
    "தமிழ் (Tamil)": dict(alert="SatCrop {tag}: உங்கள் பண்ணை அருகே {when} {hz} அபாயம் ({num}). வழிமுறைகளுக்கு செயலியைத் திறக்கவும்.",
                         sos="SatCrop அவசர உதவி: {name} ({lat:.4f}, {lon:.4f}). உடனே தொடர்பு கொள்ளவும்.",
                         test="SatCrop சோதனை செய்தி. எச்சரிக்கைகள் செயல்படுகின்றன.",
                         hz={"Drought": "வறட்சி", "Flood": "வெள்ளம்", "Cyclone": "புயல்", "Pest Outbreak": "பூச்சித் தாக்குதல்", "High Winds": "பலத்த காற்று"},
                         when={0: "இன்று", 1: "நாளை", "n": "{n} நாட்களில்"}),
    "हिन्दी (Hindi)": dict(alert="SatCrop {tag}: आपके खेत के पास {when} {hz} का खतरा ({num})। जानकारी के लिए ऐप खोलें।",
                          sos="SatCrop आपातकालीन सहायता: {name} ({lat:.4f}, {lon:.4f}). कृपया तुरंत संपर्क करें।",
                          test="SatCrop परीक्षण संदेश। अलर्ट काम कर रहे हैं।",
                          hz={"Drought": "सूखा", "Flood": "बाढ़", "Cyclone": "चक्रवात", "Pest Outbreak": "कीट प्रकोप", "High Winds": "तेज़ हवाएँ"},
                          when={0: "आज", 1: "कल", "n": "{n} दिन में"}),
}
RANK = {"INFO": 0, "IMPORT": 0, "WATCH": 1, "WARNING": 2, "ALERT": 3}
MIN_RANK = {"Watch": 1, "Warning": 2, "Alert": 3}


def sms_text(kind, hz=None, tag="", lead=None, detail="", num=""):
    """The SMS wording in the farmer's language. lead is the number of days until the hazard."""
    L = L10N.get(P("p_lang"), L10N["English"])
    when = "" if lead is None else (L["when"].get(lead) or L["when"]["n"].format(n=lead))
    return L[kind].format(tag=tag, hz=L["hz"].get(hz, hz), name=P("p_name"), lat=P("p_lat"), lon=P("p_lon"),
                          when=when, detail=detail, num=num)


def dispatch(kind, hz=None, tag="", recipients=None, lead=None, detail="", num=""):
    """Simulated notification dispatch. Nothing is really sent."""
    ss = st.session_state
    log = ss.setdefault("dispatch", [])
    text = sms_text(kind, hz, tag, lead, detail, num)
    status = "Queued (offline)" if P("s_offline") else "Delivered"
    chans = [c for c, k in (("SMS", "n_sms"), ("App push", "n_push"), ("Voice call", "n_voice")) if P(k)]
    phone = P("p_phone") or "+91 98xxx xx210 (demo)"
    rec = recipients or [f"You ({phone})"] + (["Village agriculture officer"] if tag == "ALERT" else [])
    now = datetime.now().strftime("%H:%M:%S")
    for r in rec:
        for c in chans:
            log.append({"Time": now, "Channel": c, "Recipient": r, "Status": status, "Message": text})
    del log[:-100]
    return len(rec) * len(chans)


def maybe_dispatch(tag, hz, lead=None, detail="", num=""):
    """Send the alert if it reaches the farmer's chosen level. Returns the SMS text, or None if it was held back."""
    if RANK.get(tag, 0) >= MIN_RANK.get(P("s_notify_min"), 2):
        dispatch("alert", hz, tag, lead=lead, detail=detail, num=num)
        return sms_text("alert", hz, tag, lead, detail, num)
    return None


def flush_queue():
    n = 0
    for d in st.session_state.get("dispatch", []):
        if d["Status"].startswith("Queued"):
            d["Status"] = "Delivered"; n += 1
    return n


def sync_now():
    """Go online once: refresh the forecast snapshot and deliver queued messages."""
    ss, key = st.session_state, P("s_owm_key") or os.environ.get("OPENWEATHER_API_KEY", "")
    try:
        refresh_forecast()
        prov = P("s_provider")
        if prov.startswith("Demo"):
            fc = demo_forecast(True)
        else:
            if prov.startswith("OpenWeather") and not key:
                raise ValueError("no OpenWeatherMap API key")
            fc = fetch_forecast(prov, round(P("p_lat"), 4), round(P("p_lon"), 4), key)
        ss["_wx_snap"] = dict(w=dict(fc), at=fc["fetched_at"])
        ss["_sync_msg"] = ("ok", f"Forecast updated and {flush_queue()} queued message(s) delivered.")
    except Exception as e:
        msg = str(e).replace(key, "***") if key else str(e)
        ss["_sync_msg"] = ("err", f"Sync failed: {msg[:140]}. Cached data is unchanged.")


@st.dialog("Emergency help")
def sos_dialog():
    st.markdown("**Call now**")
    st.markdown("- [112](tel:112): national emergency number\n- [1800-180-1551](tel:18001801551): Kisan Call Centre\n"
                "- [1070](tel:1070): state disaster helpline\n- [1077](tel:1077): district control room")
    st.caption("Numbers are for India. Replace them with your local helplines in a live deployment.")
    st.write(f"Your farm location: {P('p_lat'):.4f}, {P('p_lon'):.4f}")
    if st.button("Send my location to my contacts", key="sos_send"):
        n = dispatch("sos", tag="ALERT", recipients=["Emergency contact", "Village agriculture officer", "Block disaster cell"])
        st.session_state.setdefault("msgs", []).append(
            dict(ts=datetime.now(), src="SOS", tag="ALERT", text=f"SOS raised with farm coordinates. {n} notifications logged."))
        st.success(f"SOS logged ({n} notifications). This demo sends nothing. Open the SMS dispatch log to see them.")


def ticker(alerts, note=None):
    items = [f"{HAZARDS[a['hazard']]['icon']} {a['title']}: {a['text']}" for a in alerts] or \
            [note or "All clear. SatCrop is checking the live forecast for your farm."]
    txt = "     •     ".join(items)
    st.markdown(h(f'<div class="ticker"><div class="ticker-track" style="animation-duration:{max(25, len(txt) // 5)}s">{esc(txt)}</div></div>'),
                unsafe_allow_html=True)


# ───────────────────────────── Import message space and early warning feed ─────────────────────────────
KEYWORDS = {"cyclone": "Cyclone", "storm": "Cyclone", "flood": "Flood", "rain": "Flood", "drought": "Drought",
            "dry": "Drought", "pest": "Pest Outbreak", "locust": "Pest Outbreak", "wind": "High Winds", "gust": "High Winds"}


def import_msg():
    ss = st.session_state
    txt = ss.get("import_text", "").strip()
    if txt:
        found = next((v for k, v in KEYWORDS.items() if k in txt.lower()), None)
        prefix = f"[Detected: {found}] " if found else ""
        ss.setdefault("msgs", []).append(dict(ts=datetime.now(), src="Imported", tag="IMPORT", text=prefix + txt))
    ss["import_text"] = ""


def clear_feed():
    st.session_state["msgs"] = []


def early_warning_check():
    """Background check. Runs on every refresh of the alert feed (a timer re-runs it while the dashboard is open).
    It compares the live forecast with your thresholds and, for each new or worse warning, adds a message to the feed
    and sends the simulated SMS. Each hazard is announced once until it gets worse or clears."""
    ss, now = st.session_state, datetime.now()
    fc, _ = get_forecast()
    alerts = evaluate_forecast(fc)[0] if P("s_auto") else []
    msgs = ss.setdefault("msgs", [])
    if not ss.get("_engine_started"):
        ss["_engine_started"] = True
        note = ("Automatic early warnings are switched off in Settings." if not P("s_auto") else
                "Live forecast unavailable, so warnings cannot be checked." if fc.get("unavailable") else
                f"Checking the {len(fc['days'])}-day forecast for {P('p_lat'):.3f}, {P('p_lon'):.3f} against your alert thresholds.")
        msgs.append(dict(ts=now, src="Early warning engine", tag="INFO", text=note))
    fired = ss.setdefault("_fired", {})
    phone = P("p_phone") or "+91 98xxx xx210 (demo)"
    for a in alerts:
        rank = RANK[a["tag"]]
        if rank > fired.get(a["id"], 0):
            msgs.append(dict(ts=now, src="Early warning", tag=a["tag"], text=f"{a['title']}. {a['text']}"))
            sms = maybe_dispatch(a["tag"], a["hazard"], a["lead"], a["short"], a["num"])
            if sms:
                msgs.append(dict(ts=now, src=f"SMS to {phone}", tag=a["tag"], text=sms))
        fired[a["id"]] = rank
    live = {a["id"] for a in alerts}
    for hz in [k for k in fired if k not in live]:
        fired.pop(hz)
        if P("s_auto"):
            msgs.append(dict(ts=now, src="Early warning engine", tag="INFO", text=f"{HAZARDS[hz]['icon']} {hz} risk has cleared from the forecast."))
    if not P("s_offline"):
        flush_queue()
    del msgs[:-60]
    return fc, alerts


def render_feed():
    try:
        _render_feed()
    except Exception:
        st.info("The live alert feed is temporarily unavailable. It will retry on the next refresh.")


def _render_feed():
    ss = st.session_state
    fc, alerts = early_warning_check()
    msgs = ss.get("msgs", [])
    if P("s_auto"):
        alert_banners(alerts, fc)
    else:
        st.caption("Automatic early warnings are switched off in Settings. Forecasts and imported messages still show.")
    ticker(alerts, "Forecast unavailable. Warnings are paused." if fc.get("unavailable") else None)
    log = ss.get("dispatch", [])
    tab1, tab2 = st.tabs(["Live alert ticker", f"SMS dispatch log ({len(log)})"])
    with tab1:
        lines = [f"[{m['ts']:%H:%M:%S}] {m['tag']:<7} {m['src']}: {m['text']}" for m in reversed(msgs)]
        st.text_area("Live alerts", "\n".join(lines), height=270, disabled=True, label_visibility="collapsed")
        c1, c2, c3 = st.columns([5, 1.3, 1.3])
        c1.text_input("Import a message", key="import_text", placeholder="Paste an SMS or weather warning to import it",
                      label_visibility="collapsed")
        c2.button("Import", on_click=import_msg, **STRETCH)
        c3.button("Clear", on_click=clear_feed, **STRETCH)
        st.caption(f"{len(msgs)} messages. The forecast is re-checked every {P('s_refresh')} s and refreshed from the weather service every 10 minutes.")
    with tab2:
        if log:
            st.dataframe(pd.DataFrame(reversed(log)), hide_index=True, height=270, **STRETCH)
            queued = sum(d["Status"].startswith("Queued") for d in log)
            st.caption("Simulated dispatch. No real messages are sent." + (f" {queued} waiting for sync." if queued else ""))
        else:
            st.info("No messages sent yet. Warnings at or above your notification level appear here.")


# ───────────────────────────── Market data ─────────────────────────────
MARKET_BASE = {"Paddy": 2400, "Groundnut": 6300, "Sugarcane": 350, "Banana": 2700, "Tomato": 1900,
               "Maize": 2200, "Ragi": 4300, "Cotton": 7100}
MARKETS = ["Thanjavur", "Tiruchirappalli", "Kumbakonam", "Madurai", "Chennai"]
SHOCK = {  # % price rise at full intensity (supply falls)
    "Drought": dict(Paddy=8, Groundnut=12, Sugarcane=6, Banana=8, Tomato=10, Maize=9, Ragi=5, Cotton=6),
    "Flood": dict(Paddy=6, Groundnut=8, Sugarcane=3, Banana=12, Tomato=25, Maize=6, Ragi=4, Cotton=8),
    "Cyclone": dict(Paddy=8, Groundnut=6, Sugarcane=5, Banana=30, Tomato=18, Maize=7, Ragi=3, Cotton=6),
    "Pest Outbreak": dict(Paddy=6, Groundnut=5, Sugarcane=3, Banana=4, Tomato=10, Maize=5, Ragi=3, Cotton=12),
    "High Winds": dict(Paddy=4, Groundnut=3, Sugarcane=4, Banana=15, Tomato=6, Maize=6, Ragi=2, Cotton=4),
}


def market_df(S):
    rows = []
    today = datetime.now()
    for crop in CROPS:
        for mk in MARKETS:
            rng = random.Random(zlib.crc32(f"{crop}{mk}".encode()))
            price = MARKET_BASE[crop] * (1 + rng.uniform(-.05, .05))
            wk = rng.uniform(-3, 4)
            f = SHOCK[S["hz"]][crop] * S["idx"] / 100 + rng.uniform(-2, 2)
            if f >= 6: rec, days = "🔵 Hold", 10
            elif f >= 2: rec, days = "🟡 Sell in two lots", 5
            else: rec, days = "🟢 Sell now", 0
            rows.append({"Crop": crop, "Market": mk, "Today (₹/qtl)": round(price), "7-day change": round(wk, 1),
                         "14-day forecast (₹/qtl)": round(price * (1 + f / 100)), "Forecast change": round(f, 1),
                         "AI sell timing": rec, "Best sale date": (today + timedelta(days=days)).strftime("%d %b"),
                         "_days": days})
    return pd.DataFrame(rows)


# ───────────────────────────── Advisory content ─────────────────────────────
ADVICE = {
    "Drought": dict(window="5 to 7 days",
        Before=["Irrigate deeply in the early morning instead of shallow, frequent watering.", "Lay 5 to 8 cm of mulch (straw or crop residue) along the rows.", "Save water for the most sensitive stage, usually flowering or grain filling.", "Service the pump and check borewell yield and pipes."],
        During=["Irrigate only at night or before 8 AM to cut evaporation.", "Pause fertiliser top-dressing until soil moisture recovers.", "Weed early, because weeds compete for the little moisture left.", "Consider a 1% potassium nitrate foliar spray if leaves start rolling."],
        After=["Photograph wilting and yield loss with dates for insurance.", "Report crop loss to the village office if damage crosses 33%.", "Plan a short-duration or drought-tolerant crop for next season.", "Add compost or farmyard manure so soil holds more water."]),
    "Flood": dict(window="12 to 24 hours",
        Before=["Clear and deepen field drains and bunds.", "Harvest mature crop early if it is safe to do so.", "Move seed, fertiliser and pumps above the expected flood level.", "Photograph every plot for insurance records."],
        During=["Stay out of flooded fields and away from live wires.", "Move livestock to higher ground with fodder and clean water.", "Do not run electric pumps in standing water.", "Keep your phone charged and follow block office alerts."],
        After=["Drain fields within 24 to 48 hours once the water falls.", "Wash silt off leaves and spray a recommended fungicide against rot.", "Top-dress nitrogen when roots recover and re-plant lost seedlings.", "Report the loss within 72 hours for PMFBY localised calamity claims."]),
    "Cyclone": dict(window="24 to 48 hours",
        Before=["Harvest mature crop and store produce dry and off the ground.", "Stake and tie tall crops, and prop banana bunches with bamboo.", "Secure pumps, sheds and sheets, and clear loose objects.", "Move family and livestock to the cyclone shelter if told to."],
        During=["Stay indoors and do not visit the field.", "Keep radio or SMS alerts on and your phone charged.", "Switch off mains power to pumps and sheds.", "Avoid floodwater and fallen wires."],
        After=["Wait for the official all-clear before entering the field.", "Drain water, clear debris and re-stake leaning plants.", "Photograph damage and send the insurance intimation within 72 hours.", "Spray a preventive fungicide on wet-damaged crops."]),
    "Pest Outbreak": dict(window="2 to 3 days",
        Before=["Scout 20 plants along the field diagonal every 2 days.", "Set pheromone or sticky traps, about 5 per acre.", "Protect natural enemies and avoid broad-spectrum sprays.", "Keep bunds weed-free to remove alternate hosts."],
        During=["Start with neem-based sprays (5 ml per litre) or biopesticides.", "Use chemicals only above the economic threshold and follow label doses.", "Spray in the evening wearing gloves, mask and full sleeves.", "Tell neighbouring farmers so the pest is managed area-wide."],
        After=["Record scouting counts and spray dates.", "Remove and destroy heavily infested plants and residue.", "Rotate with a non-host crop next season.", "Ask your KVK or agriculture office for a pest diagnosis."]),
    "High Winds": dict(window="6 to 12 hours",
        Before=["Stake tall crops such as banana, maize and sugarcane.", "Earth up around plant bases to improve anchorage.", "Delay spraying and fertiliser until the wind calms.", "Repair windbreaks and secure nets, sheds and pipes."],
        During=["Stay out of the field and watch for flying debris.", "Turn off drip and sprinkler systems.", "Keep livestock in covered sheds.", "Note gust speeds and lodging spots if you can do so safely."],
        After=["Straighten and re-stake lodged plants within 1 to 2 days.", "Remove broken leaves and stems to prevent disease.", "Give a light irrigation to reduce stress.", "Document damage for a crop loss claim."]),
}
CROP_TIPS = {
    ("Flood", "Paddy"): "Most paddy varieties tolerate a few days of submergence. Drain fast and top-dress nitrogen once the water clears.",
    ("Flood", "Tomato"): "Tomato roots start to rot within 24 to 48 hours of waterlogging. Raise beds and drain first.",
    ("Cyclone", "Banana"): "Harvest bunches at 75 to 80% maturity before landfall and stake every plant you cannot harvest.",
    ("Wind", "Banana"): "Use bamboo props or guy ropes. Banana topples easily once gusts pass about 50 km/h.",
    ("Drought", "Groundnut"): "Protect irrigation for flowering and pegging. Mulch to keep the pegging zone moist.",
    ("Drought", "Sugarcane"): "Trash mulching cuts evaporation. Give light irrigation at tillering and grand growth.",
    ("Drought", "Paddy"): "Alternate wetting and drying saves water, but keep the field saturated at flowering.",
    ("Pest", "Cotton"): "For pink bollworm, install pheromone traps and remove rosette flowers early.",
    ("Pest", "Paddy"): "For planthoppers, avoid excess nitrogen and drain the field for a few days.",
    ("Wind", "Maize"): "Earthing up at 30 to 35 days reduces lodging.",
}
STANCE = {"Low": "Monitor conditions", "Moderate": "Prepare now", "High": "Act today", "Severe": "Act immediately"}

# ───────────────────────────── Schemes ─────────────────────────────
SCHEMES = [
    dict(id="pmk", name="PM-KISAN income support", type="Subsidy", benefit="₹6,000 a year in three instalments, paid to your bank account.",
         ownership=["Owner"], hazards=[], portal="pmkisan.gov.in",
         docs=["Aadhaar card", "Land ownership record", "Bank passbook linked to Aadhaar", "Active mobile number"]),
    dict(id="pmfby", name="PM Fasal Bima Yojana (crop insurance)", type="Insurance",
         benefit="Cover for yield loss from flood, cyclone, drought and widespread pests. Farmer premium is 2% (kharif) or 1.5% (rabi) for food crops.",
         hazards=["Drought", "Flood", "Cyclone", "Pest Outbreak", "High Winds"], portal="pmfby.gov.in",
         docs=["Aadhaar card", "Land record or tenancy proof", "Bank passbook", "Sowing declaration"]),
    dict(id="sdrf", name="SDRF/NDRF input subsidy for crop loss", type="Disaster relief",
         benefit="Cash relief per hectare (up to 2 ha per farmer) when a notified calamity damages 33% or more of the crop.",
         hazards=["Drought", "Flood", "Cyclone", "High Winds"],
         docs=["Crop damage report from village officer", "Land record", "Aadhaar card", "Bank details", "Dated photos of damage"]),
    dict(id="restr", name="Crop loan moratorium and restructuring", type="Disaster relief",
         benefit="Interest relief and extra repayment time on crop loans after a notified calamity.", needs_loan=True,
         hazards=["Drought", "Flood", "Cyclone"],
         docs=["Loan account number", "Calamity notification or damage certificate", "Written request to your bank branch"]),
    dict(id="kcc", name="Kisan Credit Card with interest subvention", type="Credit",
         benefit="Short-term crop loans up to ₹3 lakh, with an effective rate near 4% if you repay on time.", hazards=[],
         docs=["Aadhaar card", "Land record", "Passport photo", "Bank application form"]),
    dict(id="pmksy", name="PMKSY Per Drop More Crop (drip and sprinkler)", type="Subsidy",
         benefit="Subsidy of about 45% to 55% of the cost of drip or sprinkler systems.",
         irrigation=["Borewell", "Canal", "Rain-fed"], hazards=["Drought"],
         docs=["Aadhaar card", "Land record", "Water source proof", "Supplier quotation"]),
    dict(id="kusum", name="PM-KUSUM solar irrigation pump", type="Subsidy",
         benefit="Up to about 60% combined central and state support toward a solar pump, with a bank loan for part of the rest.",
         irrigation=["Borewell", "Rain-fed"], hazards=["Drought"],
         docs=["Aadhaar card", "Land record", "Electricity connection details", "Bank account details"]),
    dict(id="smam", name="Farm mechanisation subsidy (SMAM)", type="Subsidy",
         benefit="40% to 50% subsidy on tractors, sprayers and harvesters. Higher for small farmers, women, SC and ST applicants.",
         hazards=["Pest Outbreak"], docs=["Aadhaar card", "Land record", "Caste certificate (if applicable)", "Dealer quotation"]),
    dict(id="midh", name="Horticulture mission (MIDH)", type="Subsidy",
         benefit="Around 40% to 50% of project cost for planting material, protected cultivation and post-harvest units.",
         crops=["Banana", "Tomato"], hazards=["Cyclone", "High Winds"],
         docs=["Aadhaar card", "Land record", "Crop plan", "Bank details"]),
    dict(id="aif", name="Agriculture Infrastructure Fund", type="Credit",
         benefit="Loans up to ₹2 crore with 3% interest subvention for storage, cold chain and processing.", min_acres=2.5,
         hazards=["Flood", "Cyclone"], docs=["Project report", "Aadhaar card", "Land or lease document", "Bank application"]),
    dict(id="jlg", name="Joint Liability Group credit for tenant farmers", type="Credit",
         benefit="Collateral-free loans for tenant farmers who borrow as a group of 4 to 10.", ownership=["Tenant"], hazards=[],
         docs=["Aadhaar card", "Tenancy or cultivation proof", "Group formation form", "Bank account details"]),
]


def check_scheme(s):
    ok, why, fail = True, [], []
    if s.get("ownership"):
        if P("p_ownership") in s["ownership"]: why.append(f"You are a {P('p_ownership').lower()} farmer")
        else: ok = False; fail.append("Only for " + "/".join(s["ownership"]).lower() + " farmers")
    if s.get("crops"):
        if P("p_crop") in s["crops"]: why.append(f"Covers {P('p_crop')}")
        else: ok = False; fail.append("Only for " + ", ".join(s["crops"]))
    if s.get("irrigation"):
        if P("p_irrigation") in s["irrigation"]: why.append(f"Works with {P('p_irrigation').lower()} irrigation")
        else: ok = False; fail.append("Needs " + " or ".join(s["irrigation"]).lower() + " irrigation")
    if s.get("min_acres") and P("p_acres") < s["min_acres"]:
        ok = False; fail.append(f"Needs at least {s['min_acres']:g} acres")
    if s.get("needs_loan"):
        if P("p_loan"): why.append("You have an active crop loan")
        else: ok = False; fail.append("Needs an active crop loan")
    if not why and ok:
        why.append("Open to all farmers")
    return ok, why, fail


# ───────────────────────────── Land record onboarding ─────────────────────────────
def _set(key, val):
    STORE[key] = val
    st.session_state[key] = val


def apply_survey():
    """Button callback: look up the typed survey number and load its boundary and details into the farm profile."""
    ss = st.session_state
    rec, err = lookup_survey(ss.get("p_survey_input", ""))
    if err:
        ss["_survey_msg"] = ("warn", err)
        return
    try:
        lat, lon = polygon_bbox_centre(rec["polygon"])
        acres = max(0.5, round(polygon_acres(rec["polygon"]), 2))
        for k, v in dict(p_survey=rec["id"], p_survey_skip=False, p_survey_input=rec["id"], p_lat=round(lat, 6), p_lon=round(lon, 6),
                         p_acres=acres, p_name=f"{rec['owner']}'s farm", p_village=rec["village"], p_district=rec["district"],
                         p_state=rec["state"], p_crop=rec["crop"], p_soil=rec["soil"], p_irrigation=rec["irrigation"]).items():
            _set(k, v)
        ss["_survey_msg"] = ("ok", f"Found {rec['id']} in {rec['village']}, {rec['district']}: {acres:g} acres. Boundary loaded on the map.")
    except Exception:
        ss["_survey_msg"] = ("warn", "This land record could not be loaded. Please try another sample ID like SURVEY_101")


def unlink_survey():
    _set("p_survey", "")
    _set("p_survey_skip", True)
    st.session_state["_survey_msg"] = ("ok", "Land record unlinked. The farm outline is generated from your farm size again.")


def skip_survey():
    _set("p_survey_skip", True)


def survey_msg():
    msg = st.session_state.pop("_survey_msg", None)
    if msg:
        (st.warning if msg[0] == "warn" else st.success)(msg[1])


def survey_panel(onboarding=False):
    rec = SURVEYS.get(P("p_survey"))
    if rec:
        survey_msg()
        st.markdown(f"**{esc(P('p_survey'))}** linked. {esc(rec['village'])}, {esc(rec['taluk'])} taluk, {esc(rec['district'])}. "
                    f"Boundary has {len(rec['polygon'])} corner points and covers {P('p_acres'):g} acres.")
        st.button("Unlink land record", on_click=unlink_survey, key="survey_unlink")
        return
    if onboarding:
        st.markdown("**Welcome. Start by linking your land record**")
        st.caption("Enter your RTC or survey number and SatCrop loads your farm boundary, location and crop details.")
    c1, c2 = st.columns([3, 1.4], vertical_alignment="bottom")
    with c1:
        persist(st.text_input, "RTC / Survey number", "p_survey_input", DEFAULTS["p_survey_input"],
                placeholder="For example SURVEY_101", max_chars=40)
    with c2:
        st.button("Fetch land record", on_click=apply_survey, key="survey_fetch" + ("_ob" if onboarding else ""), **STRETCH)
    survey_msg()
    st.caption("Sample IDs: " + ", ".join(SURVEYS) + ". All records are synthetic.")
    if onboarding:
        st.button("Skip and explore the demo farm", on_click=skip_survey, key="survey_skip")


# ───────────────────────────── UI pieces ─────────────────────────────
def page_header(title, sub):
    st.markdown(f'<p class="page-title">{esc(title)}</p><p class="page-sub">{esc(sub)}</p>', unsafe_allow_html=True)


# ───────────────────────────── Pages ─────────────────────────────
def page_dashboard():
    onboard, hero, sos, wxc, kpi = st.container(), st.container(), st.container(), st.container(), st.container()
    left, right = st.columns([3, 2], gap="large")

    fc, _ = get_forecast()
    S = sim()
    with right:
        forecast_panel()

    with onboard:
        if not P("p_survey") and not P("p_survey_skip"):
            with st.container(border=True):
                survey_panel(onboarding=True)
        else:
            survey_msg()
    survey_chip = ('<span class="chip">' + esc(P('p_survey')) + '</span>') if P('p_survey') else ''
    if S["idx"] >= 25:
        hero_status = (f"Forecast: {HAZARDS[S['hz']]['icon']} <b>{esc(S['hz'])}</b> risk peaks {esc(when_phrase(S['day'], fc['today']))}. "
                       f"{STANCE[S['level']]}. About {S['area']:.1f} of {P('p_acres'):g} acres could be affected.")
    elif fc.get("unavailable"):
        hero_status = "The live forecast is unavailable right now, so risk cannot be checked. Do not treat this as an all-clear."
    else:
        hero_status = (f"No significant hazard is forecast for the next {len(fc['days'])} days. "
                       f"Highest watch item: {HAZARDS[S['hz']]['icon']} <b>{esc(S['hz'])}</b> ({S['level'].lower()} risk).")
    with hero:
        st.markdown(h(f"""
        <div class="hero"><div>
          <h1>{esc(P('p_name'))}</h1>
          <div class="chips"><span class="chip">{esc(P('p_village'))}, {esc(P('p_district'))}</span>
          <span class="chip">{P('p_acres'):g} acres ({farm_class(P('p_acres')).lower()})</span>
          <span class="chip">{esc(P('p_crop'))}</span><span class="chip">{esc(P('p_irrigation'))} irrigation</span>{survey_chip}</div>
          <div class="hero-status">{hero_status}</div></div>
          <div class="ring" style="--p:{S['idx']};--c:{S['color']}"><div><b>{S['idx']}</b><span>{S['level']} risk</span></div></div>
        </div>"""), unsafe_allow_html=True)
    with sos:
        c1, c2 = st.columns([2, 5], vertical_alignment="center")
        with c1:
            with st.container(key="sos_main"):
                if st.button("🆘  Emergency SOS", key="sos_btn", **STRETCH):
                    sos_dialog()
        c2.markdown('<div class="sos-note">Fire, flood rescue, injury or a crop emergency? Open helplines and alert your contacts with your farm location.</div>',
                    unsafe_allow_html=True)
    with wxc:
        weather_section()
    with kpi:
        c = st.columns(4)
        c[0].metric("Peak risk index", f"{S['idx']} / 100")
        c[1].metric("Yield at risk", f"{S['loss_pct']:.0f}%")
        c[2].metric("Area affected", f"{S['area']:.1f} acres")
        c[3].metric("Estimated loss", f"₹{S['loss']:,.0f}")
        st.caption((f"Estimates use the {S['hz'].lower()} forecast for {dpart(S['day'])} and are indicative."
                    if S["idx"] >= 25 else "No crop loss is expected on the current forecast."))

    with left:
        st.subheader("Farm twin, satellite view and crop health")
        persist(st.radio, "Map layer", "s_layer", DEFAULTS["s_layer"], options=LAYERS, horizontal=True)
        key = (f"map_{S['hz']}_{S['idx']}_{S['day']}_{P('p_acres')}_{P('s_basemap')}_{P('s_layer')}"
               f"_{P('p_lat')}_{P('p_lon')}_{P('p_survey')}_{P('p_crop')}")
        nd = None
        try:
            g = farm_geometry()
            nd = ndvi_field(g, S)
            m = build_map(S, g, nd)
            try:
                st_folium(m, height=470, use_container_width=True, returned_objects=[], key=key)
            except TypeError:
                st_folium(m, height=470, width=800, returned_objects=[], key=key)
        except Exception:
            st.info("The map could not be drawn. Check the farm coordinates in Settings, then reload.")
        if P("s_layer") != "Hazard zones":
            sw = "".join(f'<span><i style="background:{col}"></i>{name} ({NDVI_RANGE[name]})</span>' for _, name, col in NDVI_CLASSES)
            st.markdown(h(f'<div class="legend"><span><i style="background:#C6F36B"></i>Farm boundary</span>{sw}</div>'), unsafe_allow_html=True)
        if P("s_layer") != "NDVI vegetation health":
            st.markdown(h("""<div class="legend"><span><i style="background:#C6F36B"></i>Farm boundary</span>
              <span><i style="background:#5FA36B"></i>Low</span><span><i style="background:#E8A33D"></i>Moderate</span>
              <span><i style="background:#EA7A3A"></i>High</span><span><i style="background:#D64933"></i>Severe</span></div>"""),
                        unsafe_allow_html=True)
        if nd and nd["cells"]:
            st.write("")
            v = st.columns(3)
            v[0].metric("Mean NDVI (simulated)", f"{nd['mean']:.2f} {ndvi_class(nd['mean'])[0].lower()}")
            v[1].metric("Healthy area", f"{nd['share']['Healthy']:.0f}%")
            v[2].metric("Stressed or critical", f"{nd['share']['Stressed'] + nd['share']['Critical']:.0f}%")
            st.caption("NDVI is simulated from your boundary, crop and the forecast hazard, so it shows where the forecast is expected to stress the crop. Live NDVI needs Sentinel-2 bands 4 and 8 "
                       "from a service such as Sentinel Hub or Microsoft Planetary Computer.")


    st.subheader("Import message space and live alert ticker")
    st.caption("Early warnings from the live 5-day forecast, the simulated SMS sent for each, and your own imported messages.")
    st.fragment(run_every=P("s_refresh"))(render_feed)()
    with st.expander("Alert rule status (forecast vs thresholds)"):
        rules_panel()


def page_advice():
    page_header("Suggestions and advisory", "Step-by-step precautions for the hazards in your live forecast, plus where to sell.")
    fc, _ = get_forecast()
    AUTO = "Highest forecast risk"
    pick = persist(st.selectbox, "Playbook for", "hz_view", AUTO, options=[AUTO] + list(HAZARDS),
                   format_func=lambda x: x if x == AUTO else f"{HAZARDS[x]['icon']}  {x}")
    S = sim(None if pick == AUTO else pick)
    hz = S["hz"]
    if S["idx"] >= 25:
        outlook = f"Forecast: {esc(S['short'].lower())} {esc(when_phrase(S['day'], fc['today']))}."
    elif fc.get("unavailable"):
        outlook = "The live forecast is unavailable, so these steps are general preparation."
    else:
        outlook = f"No {esc(hz.lower())} is forecast in the next {len(fc['days'])} days, so these steps are for preparation."
    st.markdown(h(f"""<div class="banner" style="--c:{S['color']}"><b>{STANCE[S['level']]}: {S['level'].lower()} {esc(hz.lower())} risk</b>
      <div class="fit">Risk index {S['idx']}/100 for {P('p_acres'):g} acres of {esc(P('p_crop'))}. {outlook}
      Best action window: {ADVICE[hz]['window']}.</div></div>"""), unsafe_allow_html=True)

    left, right = st.columns([3, 2], gap="large")
    with left:
        tabs = st.tabs(["Before it hits", "While it lasts", "Recovery"])
        for tab, phase in zip(tabs, ("Before", "During", "After")):
            with tab:
                for i, step in enumerate(ADVICE[hz][phase]):
                    persist(st.checkbox, step, f"step_{hz}_{phase}_{i}", False)
        total = sum(len(ADVICE[hz][p]) for p in ("Before", "During", "After"))
        done = sum(STORE.get(f"step_{hz}_{p}_{i}", False) for p in ("Before", "During", "After") for i in range(4))
        st.progress(done / total, text=f"{done} of {total} steps completed")
    with right:
        tip = CROP_TIPS.get((HK[hz], P("p_crop")))
        with st.container(border=True):
            st.markdown(f"**Tip for {P('p_crop')}**")
            st.write(tip or f"No crop-specific note for {P('p_crop')} under {hz.lower()}. Follow the general steps and ask your local KVK.")
        with st.container(border=True):
            st.markdown("**Estimated exposure**")
            if S["idx"] >= 25:
                st.write(f"About {S['area']:.1f} acres and ₹{S['loss']:,.0f} of {P('p_crop')} revenue could be affected. "
                         f"Check the **Schemes** page for insurance and relief you may claim.")
            else:
                st.write(f"No {P('p_crop')} loss is expected from {hz.lower()} on the current forecast.")

    st.divider()
    st.subheader("Regional market prices and sell timing")
    st.caption("Mock data. The AI sell timing weighs the price trend against the hazard in your forecast, because lower supply usually lifts prices.")
    df = market_df(S)
    mine = df[df["Crop"] == P("p_crop")]
    best = mine.loc[mine["14-day forecast (₹/qtl)"].idxmax()]
    c = st.columns(3)
    c[0].metric(f"Best market for {P('p_crop')}", best["Market"])
    c[1].metric("14-day forecast", f"₹{best['14-day forecast (₹/qtl)']:,}/qtl", f"{best['Forecast change']:+.1f}%")
    c[2].metric("AI sell timing", best["AI sell timing"][2:], f"Best date {best['Best sale date']}", delta_color="off")

    only_mine = persist(st.toggle, "Show only my crop", "mkt_mine", False)
    view = (mine if only_mine else df).drop(columns="_days")
    st.dataframe(view, hide_index=True, **STRETCH, column_config={
        "Today (₹/qtl)": st.column_config.NumberColumn(format="₹%d"),
        "14-day forecast (₹/qtl)": st.column_config.NumberColumn(format="₹%d"),
        "7-day change": st.column_config.NumberColumn(format="%+.1f%%"),
        "Forecast change": st.column_config.NumberColumn(format="%+.1f%%")})
    st.markdown(f"**14-day price path for {P('p_crop')}**")
    days = np.arange(0, 15)
    path = pd.DataFrame({r["Market"]: r["Today (₹/qtl)"] + (r["14-day forecast (₹/qtl)"] - r["Today (₹/qtl)"]) * days / 14
                         for _, r in mine.iterrows()}, index=pd.Index(days, name="Days from today"))
    st.line_chart(path, height=260)


def page_schemes():
    page_header("Schemes", "Subsidies, insurance and disaster relief that match your farm profile.")
    st.caption("Details are illustrative for the demo. Confirm amounts and dates with your agriculture office before applying.")
    st.markdown(h(f"""<div class="chips"><span class="chip" style="background:#DDEFE0;color:#1E5232">{P('p_acres'):g} acres, {farm_class(P('p_acres')).lower()}</span>
      <span class="chip" style="background:#DDEFE0;color:#1E5232">{esc(P('p_crop'))}</span>
      <span class="chip" style="background:#DDEFE0;color:#1E5232">{esc(P('p_ownership'))}</span>
      <span class="chip" style="background:#DDEFE0;color:#1E5232">{esc(P('p_irrigation'))}</span>
      <span class="chip" style="background:#DDEFE0;color:#1E5232">{'Has crop loan' if P('p_loan') else 'No crop loan'}</span></div>"""),
                unsafe_allow_html=True)
    st.write("")
    f1, f2, f3 = st.columns([3, 2, 2])
    with f1:
        types = persist(st.multiselect, "Scheme type", "f_types", ["Subsidy", "Disaster relief", "Insurance", "Credit"],
                        options=["Subsidy", "Disaster relief", "Insurance", "Credit"])
    with f2: only_match = persist(st.toggle, "Only schemes I match", "f_match", True)
    with f3: only_rel = persist(st.toggle, "Only for hazards in my forecast", "f_hazard", False)
    pred = predicted_hazards()

    rows = []
    for s in SCHEMES:
        ok, why, fail = check_scheme(s)
        rel_hz = [x for x in pred if x in s["hazards"]]
        if s["type"] in types and (not only_rel or rel_hz):
            rows.append((s, ok, why, fail, rel_hz))
    rows.sort(key=lambda r: (not r[1], not r[4]))
    matched = [r for r in rows if r[1]]

    tot = sum(len(r[0]["docs"]) for r in matched)
    done = sum(STORE.get(f"doc_{r[0]['id']}_{i}", False) for r in matched for i in range(len(r[0]["docs"])))
    c = st.columns(3)
    c[0].metric("Schemes matched", f"{len(matched)} of {len(SCHEMES)}")
    c[1].metric("Relevant to my forecast", sum(1 for r in matched if r[4]))
    c[2].metric("Documents ready", f"{done} of {tot}")
    st.progress(done / tot if tot else 0.0)

    def card(s, ok, why, fail, rel_hz):
        with st.container(border=True):
            badges = f'<span class="badge b-{s["type"].split()[0]}">{s["type"]}</span>'
            if ok: badges += '<span class="badge b-match">You match</span>'
            if rel_hz: badges += f'<span class="badge b-hz">Relevant to {esc(", ".join(x.lower() for x in rel_hz))}</span>'
            portal = f' Portal: {s["portal"]}.' if s.get("portal") else ""
            fit = ("Why it fits: " + "; ".join(why)) if ok else ("Not available: " + "; ".join(fail))
            st.markdown(h(f'{badges}<div class="scheme-name">{esc(s["name"])}</div>'), unsafe_allow_html=True)
            st.write(s["benefit"])
            st.markdown(f'<div class="fit">{esc(fit)}.{esc(portal)}</div>', unsafe_allow_html=True)
            if ok:
                with st.expander("Documents checklist"):
                    for i, d in enumerate(s["docs"]):
                        persist(st.checkbox, d, f"doc_{s['id']}_{i}", False)

    for r in rows:
        if r[1]:
            card(*r)
    rest = [r for r in rows if not r[1]]
    if rest and not only_match:
        st.markdown("##### Not matching your profile")
        for r in rest:
            card(*r)
    if not rows:
        st.info("No schemes match these filters. Try adding a scheme type or turning off the hazard filter.")


def reset_all():
    for k in list(st.session_state.keys()):
        if k != "nav":
            del st.session_state[k]


def send_test():
    dispatch("test", tag="INFO")
    st.session_state["_test_sent"] = True


def page_settings():
    page_header("Settings and offline mode", "Your farm profile drives the map, advisory, prices and scheme matching.")
    t1, t2, t3, t4, t5 = st.tabs(["Farm profile", "Location and map", "Weather and alert rules",
                                  "Notifications and language", "Offline mode"])
    with t1:
        with st.container(border=True):
            st.markdown("**Land record (RTC / Survey number)**")
            survey_panel()
        linked = bool(P("p_survey"))
        a, b = st.columns(2)
        with a:
            persist(st.text_input, "Farm name", "p_name", DEFAULTS["p_name"])
            persist(st.text_input, "Village", "p_village", DEFAULTS["p_village"])
            persist(st.text_input, "District", "p_district", DEFAULTS["p_district"])
            persist(st.text_input, "State", "p_state", DEFAULTS["p_state"])
            persist(st.number_input, "Farm size (acres)", "p_acres", DEFAULTS["p_acres"], min_value=0.5, max_value=200.0, step=0.5,
                    disabled=linked)
            st.caption(f"Land class: {farm_class(P('p_acres'))}" + (". Size comes from the land record." if linked else ""))
        with b:
            persist(st.selectbox, "Main crop", "p_crop", "Paddy", options=CROPS)
            persist(st.selectbox, "Soil type", "p_soil", "Alluvial", options=["Alluvial", "Red loam", "Black cotton", "Sandy loam", "Laterite"])
            persist(st.selectbox, "Irrigation", "p_irrigation", "Canal", options=["Canal", "Borewell", "Drip", "Rain-fed"])
            persist(st.selectbox, "Land tenure", "p_ownership", "Owner", options=["Owner", "Tenant"])
            persist(st.selectbox, "Farmer category", "p_social", "General", options=["General", "SC", "ST", "Woman farmer"])
            persist(st.checkbox, "I have an active crop loan or Kisan Credit Card", "p_loan", True)
            persist(st.checkbox, "My crop is already insured", "p_insured", False)
    with t2:
        a, b = st.columns(2)
        linked = bool(P("p_survey"))
        persist(a.number_input, "Latitude", "p_lat", DEFAULTS["p_lat"], min_value=-90.0, max_value=90.0, step=0.001, format="%.4f", disabled=linked)
        persist(b.number_input, "Longitude", "p_lon", DEFAULTS["p_lon"], min_value=-180.0, max_value=180.0, step=0.001, format="%.4f", disabled=linked)
        persist(st.radio, "Map background", "s_basemap", "Satellite", options=BASEMAPS, horizontal=True)
        st.caption(("The farm boundary comes from your linked land record. Unlink it on the Farm profile tab to enter coordinates by hand."
                    if linked else "The farm outline is generated from your farm size around this point. Link a survey number on the Farm profile tab for the real boundary.")
                   + " Sentinel-2 cloudless is a free 10 m mosaic, so it looks coarser than Esri when zoomed in.")
    with t3:
        a, b = st.columns(2)
        with a:
            prov = persist(st.selectbox, "Weather source", "s_provider", DEFAULTS["s_provider"], options=PROVIDERS)
            persist(st.text_input, "OpenWeatherMap API key", "s_owm_key", "", type="password",
                    disabled=not prov.startswith("OpenWeather"),
                    help="Or set the OPENWEATHER_API_KEY environment variable. New keys can take up to two hours to activate.")
            st.caption("Open-Meteo needs no key and gives a 5-day forecast. Pick the demo storm to see warnings without internet.")
            persist(st.toggle, "Automatic weather alerts", "s_auto", True)
        with b:
            persist(st.number_input, "Cyclone warning: wind gusts above (km/h)", "s_gust", 60, min_value=20, max_value=200, step=5)
            persist(st.number_input, "Flood warning: rain in one day above (mm)", "s_rain_24", 100.0, min_value=20.0, max_value=400.0, step=5.0)
            persist(st.number_input, "Flood watch: heavy rain of at least (mm per hour)", "s_rain_h", 2.5, min_value=0.5, max_value=30.0, step=0.5)
            persist(st.number_input, "Flood watch: heavy rain for this many hours in a row", "s_rain_hrs", 3, min_value=1, max_value=12, step=1)
            persist(st.number_input, "Drought warning: dry days in a row above", "s_dry", 14, min_value=3, max_value=60, step=1)
            persist(st.number_input, "Pest watch: humidity at least (%)", "s_hum", 80, min_value=50, max_value=100, step=5)
            st.caption("A watch starts at 65% of a warning threshold and an alert at 150%. Gusts between the watch and warning level "
                       "are flagged as high winds.")
    with t4:
        a, b = st.columns(2)
        with a:
            persist(st.text_input, "Mobile number for alerts", "p_phone", "", placeholder="+91 ...")
            persist(st.selectbox, "Language for SMS and voice alerts", "p_lang", "English", options=list(L10N))
            st.caption("Dispatched alert messages use this language. Menus and advisory text stay in English in this demo.")
            persist(st.select_slider, "Alert feed refresh (seconds)", "s_refresh", 10, options=[5, 10, 20, 30])
        with b:
            st.markdown("**Channels**")
            persist(st.toggle, "SMS", "n_sms", True)
            persist(st.toggle, "App push notification", "n_push", True)
            persist(st.toggle, "Automated voice call", "n_voice", False)
            persist(st.selectbox, "Notify me from level", "s_notify_min", "Warning", options=list(MIN_RANK))
            st.button("Send a test message", on_click=send_test)
            if st.session_state.pop("_test_sent", False):
                st.success("Test message logged in the SMS dispatch log on the Dashboard.")
    with t5:
        persist(st.toggle, "Work offline (use the field cache)", "s_offline", False,
                help="Uses the last synced weather. Alerts are queued and delivered at the next sync.")
        snap, log = st.session_state.get("_wx_snap"), st.session_state.get("dispatch", [])
        queued = sum(d["Status"].startswith("Queued") for d in log)
        c = st.columns(3)
        c[0].metric("Connection", "Offline mode" if P("s_offline") else "Online")
        c[1].metric("Weather synced", f"{snap['at']:%H:%M}" if snap else "Never")
        c[2].metric("Messages waiting", queued)
        st.button("Sync now", on_click=sync_now)
        msg = st.session_state.get("_sync_msg")
        if msg:
            (st.success if msg[0] == "ok" else st.error)(msg[1])
        st.dataframe(pd.DataFrame([
            {"Data": "Weather snapshot", "Status": f"Synced {snap['at']:%d %b %H:%M}" if snap else "Needs sync"},
            {"Data": "Advisory playbooks", "Status": "Bundled, always available"},
            {"Data": "Government schemes", "Status": "Bundled, always available"},
            {"Data": "Market prices", "Status": "Mock snapshot, always available"},
            {"Data": "Satellite map tiles", "Status": "Needs a connection (boundary and zones still draw)"}]),
            hide_index=True, **STRETCH)
        st.divider()
        st.button("Reset all data to defaults", on_click=reset_all)


# ───────────────────────────── Navigation ─────────────────────────────
NAV = {"Dashboard": ("🗺️", page_dashboard), "Suggestions & Advisory": ("🌱", page_advice),
       "Schemes": ("🏛️", page_schemes), "Settings": ("⚙️", page_settings)}

with st.sidebar:
    st.markdown('<div class="brand">🛰️ SatCrop</div><div class="brand-sub">Digital Twin and Multi-Hazard Assistant</div>', unsafe_allow_html=True)
    page = st.radio("Navigate", list(NAV), format_func=lambda k: f"{NAV[k][0]}  {k}", key="nav", label_visibility="collapsed")
    st.write("")
    with st.container(key="sos_side"):
        if st.button("🆘  Emergency SOS", key="sos_btn_side", **STRETCH):
            sos_dialog()
    try:
        S0 = sim()
        waiting = sum(d["Status"].startswith("Queued") for d in st.session_state.get("dispatch", []))
        conn = f"● Offline mode, {waiting} queued" if P("s_offline") else "● Online"
        st.markdown(h(f"""<div class="side-note"><b>{esc(P('p_name'))}</b><br>{P('p_acres'):g} acres of {esc(P('p_crop'))}<br>
          Lead risk: {esc(S0['hz'])} ({S0['level'].lower()})<br>{conn}<br><br>Weather is live. Farm records, prices and schemes are samples.</div>"""),
                    unsafe_allow_html=True)
    except Exception:
        pass

try:
    NAV[page][1]()
except Exception as exc:  # last line of defence so a live demo never shows a traceback
    st.error("Something went wrong while loading this page. Your data is safe. Try another page or reload.")
    with st.expander("Technical details"):
        st.code(f"{type(exc).__name__}: {exc}")