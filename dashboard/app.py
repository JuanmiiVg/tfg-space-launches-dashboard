"""Space Launches — SpaceX-themed Analytics Dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DEMO_DATA = Path(__file__).resolve().parent / "data"

# ── Palette ────────────────────────────────────────────────────────────────────
C = {
    "bg": "#0d1b2a",
    "card": "#132030",
    "card2": "#1a2e45",
    "border": "#1e3a5f",
    "accent": "#00b4d8",
    "success": "#4ade80",
    "failure": "#f87171",
    "warning": "#fb923c",
    "text": "#e2e8f0",
    "muted": "#64748b",
}
PALETTE = [
    "#00b4d8","#0096c7","#0077b6","#023e8a",
    "#90e0ef","#48cae4","#4ade80","#a78bfa",
    "#fb923c","#f87171","#facc15","#34d399",
]


_AXIS_BASE = dict(gridcolor=C["border"], linecolor=C["border"], zeroline=False, showgrid=True, tickcolor=C["muted"])


def layout(**kw: Any) -> dict:
    """Return a Plotly layout dict; merges xaxis/yaxis with base defaults instead of replacing."""
    xaxis = {**_AXIS_BASE, **(kw.pop("xaxis", {}) or {})}
    yaxis = {**_AXIS_BASE, **(kw.pop("yaxis", {}) or {})}
    yaxis2 = kw.pop("yaxis2", None)
    base: dict = dict(
        template="none",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,27,42,0.6)",
        font=dict(color=C["text"], family="Inter, sans-serif", size=11),
        xaxis=xaxis,
        yaxis=yaxis,
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=C["border"], borderwidth=1, font=dict(size=10, color=C["text"])),
        margin=dict(l=60, r=20, t=45, b=55),
        hoverlabel=dict(bgcolor=C["card2"], font=dict(color=C["text"])),
    )
    if yaxis2 is not None:
        base["yaxis2"] = {**_AXIS_BASE, **yaxis2}
    base.update(kw)
    return base


# ── Data loaders ───────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _parquet(folder: str, demo_name: str | None = None) -> pd.DataFrame:
    # 1. Try flat demo file bundled with the dashboard (cloud-friendly)
    if demo_name:
        flat = DEMO_DATA / f"{demo_name}.parquet"
        if flat.exists():
            try:
                return pd.read_parquet(flat)
            except Exception:
                pass
    # 2. Try reading hive-partitioned directory
    path = Path(folder)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(path)
    except Exception:
        pass
    # 3. Fallback: iterate individual files
    dfs = []
    for f in path.glob("**/*.parquet"):
        try:
            dfs.append(pd.read_parquet(f))
        except Exception:
            pass
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def _coerce_year(df: pd.DataFrame) -> pd.DataFrame:
    """Convert partition-key launch_year (possibly Categorical/object) to int."""
    if "launch_year" not in df.columns:
        return df
    col = df["launch_year"]
    if hasattr(col, "cat"):
        col = col.astype(str)
    df["launch_year"] = pd.to_numeric(col, errors="coerce")
    df = df.dropna(subset=["launch_year"])
    df["launch_year"] = df["launch_year"].astype(int)
    return df


@st.cache_data(show_spinner=False)
def load_metrics() -> pd.DataFrame:
    df = _parquet(str(ROOT / "data" / "gold" / "company_year_metrics"), "metrics")
    if df.empty:
        return df
    df = _coerce_year(df)
    for col in ("total_launches", "successful_launches", "success_rate_pct"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "provider_name" in df.columns:
        df["provider_name"] = df["provider_name"].astype(str).str.strip()
    return df


@st.cache_data(show_spinner=False)
def load_features() -> pd.DataFrame:
    df = _parquet(str(ROOT / "data" / "gold" / "launch_features"), "features")
    if df.empty:
        return df
    df = _coerce_year(df)
    for col in ("is_success", "temperature_2m_mean", "wind_speed_10m_max", "launch_image_count"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "pad_country_code" in df.columns:
        df["pad_country_code"] = df["pad_country_code"].astype(str).str.strip().str.upper()
    return df


@st.cache_data(show_spinner=False)
def load_rockets() -> pd.DataFrame:
    return _parquet(str(ROOT / "data" / "silver" / "spacex_rockets"), "rockets")


def _to_float(val: Any) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@st.cache_data(show_spinner=False)
def load_raw_jsonl() -> pd.DataFrame:
    raw_dir = ROOT / "data" / "raw"
    if not raw_dir.exists():
        return pd.DataFrame()
    runs = sorted([p for p in raw_dir.iterdir() if p.is_dir()])
    if not runs:
        return pd.DataFrame()
    jfile = runs[-1] / "launch_library_launches.jsonl"
    if not jfile.exists():
        return pd.DataFrame()
    rows: list[dict] = []
    with open(jfile, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    records = []
    for r in rows:
        status = r.get("status") or {}
        prov = r.get("launch_service_provider") or {}
        rocket = (r.get("rocket") or {}).get("configuration") or {}
        mission = r.get("mission") or {}
        orbit = mission.get("orbit") or {}
        pad = r.get("pad") or {}
        loc = pad.get("location") or {}
        records.append({
            "launch_id": r.get("id"),
            "launch_name": r.get("name"),
            "net": r.get("net"),
            "status_abbrev": status.get("abbrev"),
            "provider_name": prov.get("name"),
            "provider_type": prov.get("type", "Unknown"),
            "rocket_name": rocket.get("name"),
            "rocket_family": rocket.get("family"),
            "mission_type": mission.get("type"),
            "mission_orbit": orbit.get("name") or orbit.get("abbrev"),
            "pad_country_code": pad.get("country_code"),
            "location_name": loc.get("name"),
            "pad_latitude": _to_float(pad.get("latitude")),
            "pad_longitude": _to_float(pad.get("longitude")),
        })
    df = pd.DataFrame(records)
    if "net" in df.columns:
        df["launch_year"] = pd.to_datetime(df["net"], errors="coerce", utc=True).dt.year
    if "status_abbrev" in df.columns:
        df["is_success"] = df["status_abbrev"].apply(
            lambda x: 1 if str(x).lower() == "success" else (0 if str(x).lower() in ("failure", "failed") else np.nan)
        )
    return df


@st.cache_data(show_spinner=False)
def load_images() -> pd.DataFrame:
    """Load launch images — tries bundled demo file first, then silver parquet, then raw JSONL."""
    flat = DEMO_DATA / "images.parquet"
    if flat.exists():
        try:
            df = pd.read_parquet(flat)
            if not df.empty and "image_url" in df.columns:
                if "launch_year" in df.columns:
                    df = _coerce_year(df)
                return df
        except Exception:
            pass

    silver_path = ROOT / "data" / "silver" / "images"
    if silver_path.exists():
        try:
            df = pd.read_parquet(silver_path)
            if not df.empty and "image_url" in df.columns:
                if "launch_year" in df.columns:
                    df = _coerce_year(df.rename(columns={"launch_year": "launch_year"}))
                return df
        except Exception:
            pass

    raw_dir = ROOT / "data" / "raw"
    try:
        runs = sorted([p for p in raw_dir.iterdir() if p.is_dir()])
    except Exception:
        return pd.DataFrame()
    if not runs:
        return pd.DataFrame()
    run = runs[-1]
    rows: list[dict] = []

    ll_file = run / "launch_library_images.jsonl"
    if ll_file.exists():
        with open(ll_file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    name = r.get("name", "")
                    net = r.get("net", "")
                    for url in filter(None, [r.get("image"), r.get("infographic")]):
                        rows.append({"source": "launch_library", "launch_name": name,
                                     "net": net, "image_url": url})
                except Exception:
                    pass

    sx_file = run / "spacex_launches_images.jsonl"
    if sx_file.exists():
        with open(sx_file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    name = r.get("name", "")
                    net = r.get("date_utc", "")
                    for url in (r.get("image_urls") or []):
                        if url:
                            rows.append({"source": "spacex", "launch_name": name,
                                         "net": net, "image_url": url})
                except Exception:
                    pass

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["launch_year"] = pd.to_datetime(df["net"], errors="coerce", utc=True).dt.year
    df = df.dropna(subset=["image_url", "launch_year"])
    df["launch_year"] = df["launch_year"].astype(int)
    return df


@st.cache_data(show_spinner=False)
def load_costs() -> pd.DataFrame:
    df = _parquet(str(ROOT / "data" / "silver" / "launch_costs"), "costs")
    if df.empty:
        return df
    if "launch_year" in df.columns:
        df = _coerce_year(df)
    for col in ("estimated_cost_usd", "cost_per_kg_leo_usd", "is_success"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def _rocket_image(rocket_name: str) -> str | None:
    """Return first flickr image URL for a SpaceX rocket from the raw JSON, if available."""
    raw_dir = ROOT / "data" / "raw"
    try:
        runs = sorted([p for p in raw_dir.iterdir() if p.is_dir()])
        if not runs:
            return None
        jfile = runs[-1] / "spacex_rockets.json"
        if not jfile.exists():
            return None
        with open(jfile, encoding="utf-8") as fh:
            data = json.load(fh)
        for rocket in data:
            if rocket.get("name") == rocket_name:
                imgs = rocket.get("flickr_images", [])
                return imgs[0] if imgs else None
    except Exception:
        return None
    return None


# ── CSS ────────────────────────────────────────────────────────────────────────

def inject_css() -> None:
    import base64, random
    rng = random.Random(42)
    circles = "".join(
        f'<circle cx="{rng.randint(0,800)}" cy="{rng.randint(0,800)}" '
        f'r="{rng.choice([0.7,0.9,1.2,1.8,0.7])}" '
        f'fill="{rng.choice(["#fff","#fff","#fff","#90e0ef","#caf0f8"])}" '
        f'opacity="{rng.uniform(0.2,0.88):.2f}"/>'
        for _ in range(200)
    )
    svg_data = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800">{circles}</svg>'
    star_bg = "data:image/svg+xml;base64," + base64.b64encode(svg_data.encode()).decode()

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500;600&display=swap');

/* ═══════════════════════════════════════════
   APP — animated starfield background
═══════════════════════════════════════════ */
.stApp {{
    background-color: {C['bg']};
    background-image:
        url("{star_bg}"),
        radial-gradient(ellipse at 20% 5%,  #0f2744 0%, transparent 52%),
        radial-gradient(ellipse at 80% 95%, #060d1a 0%, transparent 52%);
    background-size:     700px 700px, cover, cover;
    background-position: 0 0, 50% 5%, 50% 95%;
    background-repeat:   repeat, no-repeat, no-repeat;
    font-family: 'Inter', sans-serif;
    color: {C['text']};
    animation: starDrift 350s linear infinite;
}}
@keyframes starDrift {{
    from {{ background-position: 0px 0px,     50% 5%,  50% 95%; }}
    to   {{ background-position: 700px 700px, 50% 5%,  50% 95%; }}
}}
.main .block-container {{ padding-top: 0.75rem; max-width: 1400px; }}

/* ═══════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════ */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #040810 0%, #080f1c 100%) !important;
    border-right: 1px solid {C['border']};
    position: relative;
}}
[data-testid="stSidebar"]::after {{
    content: '';
    position: absolute;
    top: 8%; right: 0;
    width: 1px; height: 84%;
    background: linear-gradient(180deg, transparent, {C['accent']}70, transparent);
    animation: sideGlow 5s ease-in-out infinite;
}}
@keyframes sideGlow {{
    0%, 100% {{ opacity: 0.3; }}
    50%       {{ opacity: 1;   }}
}}
[data-testid="stSidebar"] * {{ color: {C['text']}; }}
[data-testid="stSidebar"] h3 {{
    color: {C['accent']} !important;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}}

/* ═══════════════════════════════════════════
   KPI CARDS — shimmer + hover lift
═══════════════════════════════════════════ */
[data-testid="metric-container"] {{
    background: linear-gradient(135deg, {C['card2']} 0%, {C['card']} 100%);
    border: 1px solid {C['border']};
    border-radius: 12px;
    padding: 1rem 1.25rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.22s ease, box-shadow 0.22s ease;
    animation: cardPulse 5s ease-in-out infinite;
}}
[data-testid="metric-container"]:hover {{
    transform: translateY(-5px) scale(1.025);
    box-shadow: 0 14px 40px rgba(0,180,216,0.28) !important;
}}
[data-testid="metric-container"]::before {{
    content: '';
    position: absolute;
    top: 0; left: -120%;
    width: 60%; height: 2px;
    background: linear-gradient(90deg, transparent, {C['accent']}dd, transparent);
    animation: shimmerCard 3.5s ease-in-out infinite;
}}
@keyframes shimmerCard {{
    0%   {{ left: -120%; }}
    100% {{ left:  220%; }}
}}
@keyframes cardPulse {{
    0%, 100% {{ box-shadow: 0 0 12px rgba(0,180,216,0.04), inset 0 1px 0 rgba(0,180,216,0.04); }}
    50%       {{ box-shadow: 0 0 28px rgba(0,180,216,0.13), inset 0 1px 0 rgba(0,180,216,0.09); }}
}}
[data-testid="stMetricLabel"] p {{
    color: {C['muted']} !important;
    font-size: 0.68rem !important;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}
[data-testid="stMetricValue"] {{
    color: {C['accent']} !important;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 1.55rem !important;
    font-weight: 700 !important;
}}

/* ═══════════════════════════════════════════
   SECTION TITLES — underline grow
═══════════════════════════════════════════ */
.sec-title {{
    font-family: 'Orbitron', sans-serif;
    font-size: 0.78rem;
    color: {C['accent']};
    text-transform: uppercase;
    letter-spacing: 0.14em;
    border-left: 3px solid {C['accent']};
    padding-left: 0.75rem;
    margin: 1.5rem 0 1rem;
    position: relative;
    text-shadow: 0 0 10px rgba(0,180,216,0.35);
}}
.sec-title::after {{
    content: '';
    position: absolute;
    bottom: -3px; left: 0.75rem;
    height: 1px; width: 0;
    background: linear-gradient(90deg, {C['accent']}90, transparent);
    animation: growLine 1.4s ease-out forwards;
}}
@keyframes growLine {{
    from {{ width: 0;   opacity: 0; }}
    to   {{ width: 55%; opacity: 1; }}
}}

/* ═══════════════════════════════════════════
   HERO — scan line + orb pulse + title glow
═══════════════════════════════════════════ */
.hero {{
    background: linear-gradient(135deg, #060f1e 0%, #0a1f35 45%, #061020 100%);
    border: 1px solid {C['border']};
    border-radius: 16px;
    padding: 1.75rem 2.25rem;
    margin-bottom: 1.25rem;
    position: relative;
    overflow: hidden;
}}
/* top accent bar that pulses */
.hero::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, {C['accent']} 50%, transparent 100%);
    animation: heroBar 4s ease-in-out infinite;
}}
@keyframes heroBar {{
    0%, 100% {{ opacity: 0.25; transform: scaleX(0.4); }}
    50%       {{ opacity: 1;   transform: scaleX(1);   }}
}}
/* right glow orb */
.hero::after {{
    content: '';
    position: absolute;
    top: -60%; right: -5%;
    width: 55%; height: 220%;
    background: radial-gradient(ellipse, rgba(0,180,216,0.10) 0%, transparent 65%);
    pointer-events: none;
    animation: heroOrb 7s ease-in-out infinite alternate;
}}
@keyframes heroOrb {{
    from {{ opacity: 0.6; transform: scale(1)    translateX(0px);  }}
    to   {{ opacity: 1;   transform: scale(1.18) translateX(18px); }}
}}
.hero-title {{
    font-family: 'Orbitron', sans-serif;
    font-size: 1.85rem;
    font-weight: 900;
    color: #fff;
    margin: 0;
    line-height: 1.25;
    animation: titleGlow 4s ease-in-out infinite alternate;
}}
@keyframes titleGlow {{
    from {{ text-shadow: 0 0 22px rgba(0,180,216,0.45), 0 0 55px rgba(0,180,216,0.15); }}
    to   {{ text-shadow: 0 0 38px rgba(0,180,216,0.80), 0 0 85px rgba(0,180,216,0.32), 0 0 130px rgba(0,180,216,0.12); }}
}}
.hero-sub {{
    color: {C['accent']};
    font-size: 0.75rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    margin-top: 0.45rem;
}}
/* floating stat pills */
.pill {{
    display: inline-block;
    border-radius: 20px;
    padding: 0.2rem 0.75rem;
    font-size: 0.72rem;
    margin: 0.25rem 0.2rem 0;
    animation: pillFloat 3.2s ease-in-out infinite alternate;
}}
.pill:nth-child(2) {{ animation-delay: 0.6s; }}
.pill:nth-child(3) {{ animation-delay: 1.2s; }}
.pill:nth-child(4) {{ animation-delay: 1.8s; }}
@keyframes pillFloat {{
    from {{ transform: translateY(0px);  }}
    to   {{ transform: translateY(-4px); }}
}}

/* ═══════════════════════════════════════════
   TABS
═══════════════════════════════════════════ */
.stTabs [role="tablist"] {{
    background: transparent;
    border-bottom: 1px solid {C['border']};
    gap: 0.1rem;
}}
.stTabs [role="tab"] {{
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    color: {C['muted']};
    font-weight: 500;
    border-radius: 8px 8px 0 0;
    transition: color 0.2s ease, background 0.2s ease;
    padding: 0.45rem 0.8rem;
}}
.stTabs [role="tab"]:hover {{
    color: {C['text']} !important;
    background: rgba(0,180,216,0.07) !important;
}}
.stTabs [aria-selected="true"] {{
    color: {C['accent']} !important;
    border-bottom: 2px solid {C['accent']} !important;
    background: rgba(0,180,216,0.07) !important;
    text-shadow: 0 0 8px rgba(0,180,216,0.45);
}}

/* ═══════════════════════════════════════════
   SCROLLBAR
═══════════════════════════════════════════ */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: {C['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {C['border']}; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {C['accent']}; box-shadow: 0 0 6px {C['accent']}; }}

/* ═══════════════════════════════════════════
   MISC
═══════════════════════════════════════════ */
hr {{
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent 0%, rgba(0,180,216,0.38) 40%, rgba(0,180,216,0.38) 60%, transparent 100%) !important;
    margin: 1.25rem 0 !important;
}}
[data-testid="stDataFrame"] {{
    border: 1px solid {C['border']} !important;
    border-radius: 8px;
    overflow: hidden;
}}
</style>""", unsafe_allow_html=True)


# ── Hero ───────────────────────────────────────────────────────────────────────

def render_hero(total: int, rate: float, n_years: int, providers: int) -> None:
    st.markdown(f"""
<div class="hero">
  <div class="hero-title">SPACE LAUNCHES<br/>DATA &amp; ANALYTICS</div>
  <div class="hero-sub">Explorando el universo — Impulsando el futuro</div>
  <div style="margin-top:1rem;">
    <span class="pill" style="background:rgba(0,180,216,0.15);border:1px solid rgba(0,180,216,0.35);color:{C['accent']};">
      {total:,} lanzamientos
    </span>
    <span class="pill" style="background:rgba(74,222,128,0.1);border:1px solid rgba(74,222,128,0.35);color:#4ade80;">
      {rate:.1f}% tasa de éxito
    </span>
    <span class="pill" style="background:rgba(167,139,250,0.1);border:1px solid rgba(167,139,250,0.35);color:#a78bfa;">
      {n_years} años de historia
    </span>
    <span class="pill" style="background:rgba(251,146,60,0.1);border:1px solid rgba(251,146,60,0.35);color:#fb923c;">
      {providers} agencias espaciales
    </span>
  </div>
</div>""", unsafe_allow_html=True)


# ── KPIs ───────────────────────────────────────────────────────────────────────

def render_kpis(mf: pd.DataFrame, ff: pd.DataFrame) -> None:
    total = int(mf["total_launches"].sum())
    succ = int(mf["successful_launches"].sum()) if "successful_launches" in mf.columns else 0
    rate = round(succ / total * 100, 1) if total else 0.0
    provs = mf["provider_name"].nunique()
    countries = ff["pad_country_code"].nunique() if "pad_country_code" in ff.columns else 0
    orbits = ff["mission_orbit"].nunique() if "mission_orbit" in ff.columns else 0
    temp = ff["temperature_2m_mean"].mean() if "temperature_2m_mean" in ff.columns else None
    wind = ff["wind_speed_10m_max"].mean() if "wind_speed_10m_max" in ff.columns else None

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Total Lanzamientos", f"{total:,}")
    c2.metric("Tasa de Éxito", f"{rate:.1f}%")
    c3.metric("Agencias", str(provs))
    c4.metric("Países", str(countries))
    c5.metric("Tipos Órbita", str(orbits))
    c6.metric("Temp. Media", f"{temp:.1f}°C" if temp and not np.isnan(temp) else "—")
    c7.metric("Viento Medio", f"{wind:.1f} km/h" if wind and not np.isnan(wind) else "—")


# ── Tab 1: Histórico ───────────────────────────────────────────────────────────

def tab_historico(mf: pd.DataFrame, ff: pd.DataFrame) -> None:
    st.markdown('<div class="sec-title">Actividad de Lanzamientos por Año</div>', unsafe_allow_html=True)

    yearly = (
        mf.groupby("launch_year")
        .agg(total=("total_launches", "sum"), success=("successful_launches", "sum"))
        .reset_index()
        .sort_values("launch_year")
    )
    yearly["failed"] = (yearly["total"] - yearly["success"]).clip(lower=0)
    yearly["rate"] = (yearly["success"] / yearly["total"].replace(0, np.nan) * 100).round(2)
    yearly["rolling"] = yearly["rate"].rolling(5, min_periods=1).mean()
    # Convert to plain Python lists to avoid numpy int32/int64 dtype issues with Plotly
    yrs = yearly["launch_year"].astype(int).tolist()
    succ = yearly["success"].tolist()
    fail = yearly["failed"].tolist()
    rate = yearly["rate"].tolist()
    roll = yearly["rolling"].tolist()

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=yrs, y=succ, name="Exitosos",
                             marker=dict(color=C["success"])))
        fig.add_trace(go.Bar(x=yrs, y=fail, name="Fallidos",
                             marker=dict(color=C["failure"])))
        fig.update_layout(**layout(
            title=dict(text="Lanzamientos por Año", font=dict(size=13, color=C["text"])),
            barmode="stack",
            xaxis=dict(title="Año"),
            yaxis=dict(title="Lanzamientos"),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    with c2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=yrs, y=rate, mode="markers",
            marker=dict(color=C["accent"], size=5, opacity=0.5),
            name="Tasa anual",
        ))
        fig.add_trace(go.Scatter(
            x=yrs, y=roll, mode="lines",
            line=dict(color=C["accent"], width=2.5),
            fill="tozeroy", fillcolor="rgba(0,180,216,0.1)",
            name="Media móvil 5 años",
        ))
        fig.update_layout(**layout(
            title=dict(text="Tasa de Éxito Global (%) — Media Móvil 5 Años", font=dict(size=13, color=C["text"])),
            xaxis=dict(title="Año"),
            yaxis=dict(title="%", range=[0, 110]),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    st.markdown('<div class="sec-title">Evolución de los Top 5 Proveedores</div>', unsafe_allow_html=True)
    top5 = mf.groupby("provider_name")["total_launches"].sum().nlargest(5).index.tolist()
    df5 = mf[mf["provider_name"].isin(top5)].copy()
    df5["launch_year"] = df5["launch_year"].astype(int)
    df5["total_launches"] = df5["total_launches"].astype(float)
    if not df5.empty:
        fig = go.Figure()
        for i, prov in enumerate(top5):
            pdf = df5[df5["provider_name"] == prov].sort_values("launch_year")
            fig.add_trace(go.Scatter(
                x=pdf["launch_year"].tolist(),
                y=pdf["total_launches"].tolist(),
                name=prov, mode="lines",
                stackgroup="one",
                line=dict(color=PALETTE[i % len(PALETTE)], width=1.5),
            ))
        fig.update_layout(**layout(
            title=dict(text="Lanzamientos Anuales — Top 5 Agencias", font=dict(size=13, color=C["text"])),
            xaxis=dict(title="Año"),
            yaxis=dict(title="Lanzamientos"),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)
    else:
        st.info("Sin datos para los proveedores seleccionados.")

    st.markdown('<div class="sec-title">Acumulado Histórico</div>', unsafe_allow_html=True)
    yearly["cumulative"] = yearly["total"].cumsum()
    yearly["cum_success"] = yearly["success"].cumsum()
    cum = yearly["cumulative"].tolist()
    cum_s = yearly["cum_success"].tolist()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=yrs, y=cum, mode="lines", fill="tozeroy",
        line=dict(color=C["accent"], width=2.5),
        fillcolor="rgba(0,180,216,0.1)", name="Total acumulado",
    ))
    fig.add_trace(go.Scatter(
        x=yrs, y=cum_s, mode="lines",
        line=dict(color=C["success"], width=2, dash="dot"),
        name="Éxitos acumulados",
    ))
    fig.update_layout(**layout(
        title=dict(text="Lanzamientos Acumulados a lo Largo de la Historia", font=dict(size=13, color=C["text"])),
        xaxis=dict(title="Año"),
        yaxis=dict(title="Lanzamientos acumulados"),
    ))
    st.plotly_chart(fig, use_container_width=True, theme=None)

    # ── Heatmap estacional ──
    st.markdown('<div class="sec-title">Estacionalidad — Lanzamientos por Mes y Año</div>', unsafe_allow_html=True)
    heatmap_src = ff if not ff.empty and "launch_date" in ff.columns else pd.DataFrame()
    if not heatmap_src.empty:
        hdf = heatmap_src.copy()
        hdf["_dt"] = pd.to_datetime(hdf["launch_date"], errors="coerce", utc=False)
        hdf = hdf.dropna(subset=["_dt"])
        hdf["_month"] = hdf["_dt"].dt.month
        hdf["_year"] = hdf["_dt"].dt.year.astype(int)
        yr_min, yr_max = int(mf["launch_year"].min()), int(mf["launch_year"].max())
        hdf = hdf[(hdf["_year"] >= yr_min) & (hdf["_year"] <= yr_max)]
        pivot = hdf.groupby(["_year", "_month"]).size().reset_index(name="cnt")
        mat = pivot.pivot(index="_year", columns="_month", values="cnt").reindex(
            columns=range(1, 13), fill_value=0
        ).fillna(0)
        months_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                     "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        fig_h = go.Figure(go.Heatmap(
            z=mat.values.tolist(),
            x=months_es,
            y=[str(y) for y in mat.index.tolist()],
            colorscale=[[0, "#0a0f1a"], [0.05, "#0a2a4a"],
                        [0.3, "#023e8a"], [0.65, C["accent"]], [1, "#90e0ef"]],
            zmin=0,
            hoverongaps=False,
            hovertemplate="<b>%{y} — %{x}</b><br>Lanzamientos: %{z:.0f}<extra></extra>",
            colorbar=dict(
                tickfont=dict(color=C["text"]),
                title=dict(text="N°", font=dict(color=C["text"])),
            ),
        ))
        fig_h.update_layout(**layout(
            title=dict(text="Lanzamientos por Mes — ¿Hay estacionalidad?", font=dict(size=13)),
            xaxis=dict(title="", side="top", tickfont=dict(size=11)),
            yaxis=dict(title="", autorange="reversed", tickfont=dict(size=10)),
            height=max(280, len(mat) * 18 + 80),
            margin=dict(l=60, r=20, t=80, b=20),
        ))
        st.plotly_chart(fig_h, use_container_width=True, theme=None)


# ── Tab 2: Proveedores ─────────────────────────────────────────────────────────

def tab_proveedores(mf: pd.DataFrame) -> None:
    st.markdown('<div class="sec-title">Ranking de Proveedores</div>', unsafe_allow_html=True)

    stats = (
        mf.groupby("provider_name")
        .agg(total=("total_launches", "sum"), success=("successful_launches", "sum"))
        .reset_index()
    )
    stats["rate"] = (stats["success"] / stats["total"] * 100).round(1)

    c1, c2 = st.columns(2)
    with c1:
        top12 = stats.nlargest(12, "total")
        fig = px.bar(top12, x="total", y="provider_name", orientation="h",
                     color="total",
                     color_continuous_scale=[[0, "#023e8a"], [0.5, "#0096c7"], [1, "#00b4d8"]])
        fig.update_layout(**layout(
            title=dict(text="Top 12 Agencias — Total Lanzamientos", font=dict(size=13)),
            showlegend=False, coloraxis_showscale=False,
            xaxis=dict(title="Lanzamientos"), yaxis=dict(title=""),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    with c2:
        top10r = stats.nlargest(10, "total")
        fig = go.Figure(go.Bar(
            x=top10r["provider_name"], y=top10r["rate"],
            marker=dict(
                color=top10r["rate"],
                colorscale=[[0, C["failure"]], [0.5, C["warning"]], [1, C["success"]]],
                cmin=0, cmax=100,
            ),
            hovertemplate="<b>%{x}</b><br>Tasa: %{y:.1f}%<extra></extra>",
        ))
        fig.update_layout(**layout(
            title=dict(text="Tasa de Éxito — Top 10 Agencias (%)", font=dict(size=13)),
            xaxis=dict(tickangle=-38, title=""),
            yaxis=dict(range=[0, 105], title="Tasa de éxito (%)"),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    st.markdown('<div class="sec-title">Tendencia Comparativa de Tasa de Éxito</div>', unsafe_allow_html=True)
    top6 = stats.nlargest(6, "total")["provider_name"].tolist()
    df6 = mf[mf["provider_name"].isin(top6)].copy()
    fig = go.Figure()
    for i, prov in enumerate(top6):
        pdf = df6[df6["provider_name"] == prov].sort_values("launch_year")
        fig.add_trace(go.Scatter(
            x=pdf["launch_year"].tolist(),
            y=pdf["success_rate_pct"].tolist(),
            name=prov, mode="lines+markers",
            line=dict(color=PALETTE[i % len(PALETTE)], width=2),
            marker=dict(size=5, color=PALETTE[i % len(PALETTE)]),
        ))
    fig.update_layout(**layout(
        title=dict(text="Tasa de Éxito Anual por Agencia — Top 6", font=dict(size=13)),
        xaxis=dict(title="Año"), yaxis=dict(range=[0, 105], title="%"),
    ))
    st.plotly_chart(fig, use_container_width=True, theme=None)

    st.markdown('<div class="sec-title">Distribución de Lanzamientos</div>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        top8 = stats.nlargest(8, "total")
        other = pd.DataFrame([{"provider_name": "Otros",
                                "total": stats[~stats["provider_name"].isin(top8["provider_name"])]["total"].sum()}])
        pie_df = pd.concat([top8[["provider_name", "total"]], other], ignore_index=True)
        fig = px.pie(pie_df, values="total", names="provider_name", hole=0.45,
                     color_discrete_sequence=PALETTE)
        fig.update_traces(
            marker=dict(line=dict(color=C["bg"], width=2)),
            textfont_size=10, textposition="inside",
        )
        fig.update_layout(**layout(
            title=dict(text="Participación de Mercado", font=dict(size=13)),
            showlegend=True,
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    with c4:
        st.markdown("**Tabla resumen de agencias**")
        disp = stats.nlargest(15, "total").copy()
        disp["rate"] = disp["rate"].apply(lambda x: f"{x:.1f}%")
        disp = disp.rename(columns={
            "provider_name": "Agencia", "total": "Lanzamientos",
            "success": "Exitosos", "rate": "Tasa Éxito",
        })
        st.dataframe(disp.reset_index(drop=True), use_container_width=True, hide_index=True)

    # ── Bar chart race ──
    st.markdown('<div class="sec-title">Carrera Espacial — Evolución Acumulada</div>', unsafe_allow_html=True)
    years_race = sorted(mf["launch_year"].unique())
    top15 = mf.groupby("provider_name")["total_launches"].sum().nlargest(15).index.tolist()
    running: dict[str, int] = {a: 0 for a in top15}
    frames_race: list[go.Frame] = []
    init_bar = None
    for yr in years_race:
        yd = mf[mf["launch_year"] == yr].groupby("provider_name")["total_launches"].sum()
        for a in top15:
            running[a] += int(yd.get(a, 0))
        sorted_data = sorted([(a, running[a]) for a in top15], key=lambda x: x[1])
        yv = [a for a, _ in sorted_data]
        xv = [v for _, v in sorted_data]
        clrs = [PALETTE[top15.index(a) % len(PALETTE)] for a in yv]
        bar = go.Bar(
            x=xv, y=yv, orientation="h",
            marker=dict(color=clrs, opacity=0.85),
            text=[f"{v:,}" for v in xv],
            textposition="outside",
            textfont=dict(color=C["text"], size=9),
            hovertemplate="%{y}: %{x:,}<extra></extra>",
        )
        frames_race.append(go.Frame(
            data=[bar], name=str(int(yr)),
            layout=go.Layout(
                xaxis=dict(range=[0, max(xv) * 1.18] if xv else [0, 10]),
                annotations=[dict(
                    text=str(int(yr)), x=0.97, y=0.03,
                    xref="paper", yref="paper", showarrow=False,
                    font=dict(size=38, color="rgba(0,180,216,0.18)", family="Orbitron"),
                    xanchor="right", yanchor="bottom",
                )],
            ),
        ))
        if init_bar is None:
            init_bar = bar
    if frames_race and init_bar is not None:
        fig_race = go.Figure(data=[init_bar], frames=frames_race)
        fig_race.update_layout(**layout(
            title=dict(text="Top 15 Agencias — Lanzamientos Acumulados (presiona ▶)", font=dict(size=13)),
            xaxis=dict(title="Lanzamientos acumulados"),
            yaxis=dict(title=""),
            height=520,
            margin=dict(l=160, r=70, t=55, b=55),
        ))
        fig_race.update_layout(
            updatemenus=[dict(
                type="buttons", showactive=False,
                y=1.08, x=0.5, xanchor="center",
                buttons=[
                    dict(label="▶  Play", method="animate",
                         args=[None, dict(frame=dict(duration=650, redraw=True),
                                          fromcurrent=True,
                                          transition=dict(duration=400, easing="cubic-in-out"))]),
                    dict(label="⏸  Pausa", method="animate",
                         args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
                ],
                font=dict(color=C["text"], size=12),
                bgcolor=C["card"], bordercolor=C["border"],
            )],
            sliders=[dict(
                active=0,
                currentvalue=dict(font=dict(size=13, color=C["accent"]), prefix="Año: ",
                                  visible=True, xanchor="right"),
                transition=dict(duration=400, easing="cubic-in-out"),
                pad=dict(b=10, t=60), len=0.88, x=0.06,
                font=dict(color=C["muted"], size=9),
                steps=[dict(
                    args=[[str(int(y))], dict(frame=dict(duration=650, redraw=True),
                                              mode="immediate",
                                              transition=dict(duration=400))],
                    label=str(int(y)), method="animate",
                ) for y in years_race],
            )],
        )
        st.plotly_chart(fig_race, use_container_width=True, theme=None)


# ── Tab 3: Misiones & Órbitas ──────────────────────────────────────────────────

def tab_misiones(ff: pd.DataFrame, raw_df: pd.DataFrame) -> None:
    st.markdown('<div class="sec-title">Tipos de Misión y Distribución Orbital</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        col = "mission_type"
        src = ff if col in ff.columns else raw_df.rename(columns={"mission_type": col}) if "mission_type" in raw_df.columns else pd.DataFrame()
        if not src.empty and col in src.columns:
            mt = src[col].dropna().value_counts().reset_index()
            mt.columns = ["type", "count"]
            fig = px.pie(mt, values="count", names="type", hole=0.48,
                         color_discrete_sequence=PALETTE)
            fig.update_traces(marker=dict(line=dict(color=C["bg"], width=2)), textfont_size=9)
            fig.update_layout(**layout(
                title=dict(text="Tipos de Misión", font=dict(size=13)),
                legend=dict(font=dict(size=9)),
            ))
            st.plotly_chart(fig, use_container_width=True, theme=None)

    with c2:
        col = "mission_orbit"
        if col in ff.columns:
            orb = ff[col].dropna().value_counts().reset_index()
            orb.columns = ["orbit", "count"]
            fig = px.pie(orb, values="count", names="orbit", hole=0.48,
                         color_discrete_sequence=PALETTE[::-1])
            fig.update_traces(marker=dict(line=dict(color=C["bg"], width=2)), textfont_size=9)
            fig.update_layout(**layout(
                title=dict(text="Distribución de Órbitas", font=dict(size=13)),
                legend=dict(font=dict(size=9)),
            ))
            st.plotly_chart(fig, use_container_width=True, theme=None)

    st.markdown('<div class="sec-title">Órbitas a lo Largo del Tiempo</div>', unsafe_allow_html=True)
    if "mission_orbit" in ff.columns and "launch_year" in ff.columns:
        top_orbits = ff["mission_orbit"].value_counts().head(6).index.tolist()
        orb_time = (
            ff[ff["mission_orbit"].isin(top_orbits)]
            .groupby(["launch_year", "mission_orbit"])
            .size()
            .reset_index(name="count")
        )
        fig = go.Figure()
        for i, orbit in enumerate(top_orbits):
            odf = orb_time[orb_time["mission_orbit"] == orbit].sort_values("launch_year")
            fig.add_trace(go.Scatter(
                x=odf["launch_year"].tolist(),
                y=odf["count"].tolist(),
                name=orbit, mode="lines",
                stackgroup="one",
                line=dict(color=PALETTE[i % len(PALETTE)], width=1.5),
            ))
        fig.update_layout(**layout(
            title=dict(text="Lanzamientos por Tipo de Órbita — Evolución", font=dict(size=13)),
            xaxis=dict(title="Año"), yaxis=dict(title="Lanzamientos"),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    st.markdown('<div class="sec-title">Éxito por Tipo de Misión</div>', unsafe_allow_html=True)
    if "mission_type" in ff.columns and "is_success" in ff.columns:
        ms = (
            ff.groupby("mission_type")
            .agg(total=("is_success", "count"), success=("is_success", "sum"))
            .reset_index()
        )
        ms["rate"] = (ms["success"] / ms["total"] * 100).round(1)
        ms = ms.sort_values("total", ascending=False).head(10)
        c3, c4 = st.columns(2)
        with c3:
            fig = px.bar(ms, x="mission_type", y="total", color="rate",
                         color_continuous_scale=[[0, C["failure"]], [0.5, C["warning"]], [1, C["success"]]])
            fig.update_layout(**layout(
                title=dict(text="Lanzamientos por Tipo de Misión", font=dict(size=13)),
                xaxis=dict(tickangle=-35, title=""),
                coloraxis_colorbar=dict(title="Tasa %"),
            ))
            st.plotly_chart(fig, use_container_width=True, theme=None)
        with c4:
            fig = px.bar(ms, x="mission_type", y="rate",
                         color="rate",
                         color_continuous_scale=[[0, C["failure"]], [0.5, C["warning"]], [1, C["success"]]],
                         range_y=[0, 105])
            fig.update_layout(**layout(
                title=dict(text="Tasa de Éxito por Tipo de Misión (%)", font=dict(size=13)),
                xaxis=dict(tickangle=-35, title=""),
                yaxis=dict(title="%"),
                showlegend=False, coloraxis_showscale=False,
            ))
            st.plotly_chart(fig, use_container_width=True, theme=None)


# ── Tab 4: Geografía ───────────────────────────────────────────────────────────

def tab_geografia(ff: pd.DataFrame) -> None:
    st.markdown('<div class="sec-title">Mapa Global de Sitios de Lanzamiento</div>', unsafe_allow_html=True)

    if all(c in ff.columns for c in ("pad_latitude", "pad_longitude")):
        geo = ff.dropna(subset=["pad_latitude", "pad_longitude"]).copy()

        # Aggregate launches per pad so dot size reflects launch volume
        grp_cols = ["pad_latitude", "pad_longitude", "pad_country_code"]
        pad_grp = geo.groupby(grp_cols)
        pad_stats = pad_grp.size().reset_index(name="total")
        if "is_success" in geo.columns:
            succ = pad_grp["is_success"].sum().reset_index(name="success")
            pad_stats = pad_stats.merge(succ, on=grp_cols)
            pad_stats["success_rate"] = (pad_stats["success"] / pad_stats["total"] * 100).round(1)
        else:
            pad_stats["success_rate"] = 50.0
        if "location_name" in geo.columns:
            locs = geo.groupby(grp_cols)["location_name"].first().reset_index()
            pad_stats = pad_stats.merge(locs, on=grp_cols, how="left")
            pad_stats["label"] = pad_stats["location_name"].fillna(pad_stats["pad_country_code"])
        else:
            pad_stats["label"] = pad_stats["pad_country_code"]
        max_t = pad_stats["total"].max() or 1
        pad_stats["dot_size"] = (pad_stats["total"] / max_t * 20 + 5).clip(lower=5, upper=25)

        fig = go.Figure()
        fig.add_trace(go.Scattergeo(
            lat=pad_stats["pad_latitude"].tolist(),
            lon=pad_stats["pad_longitude"].tolist(),
            mode="markers",
            marker=dict(
                size=pad_stats["dot_size"].tolist(),
                color=pad_stats["success_rate"].tolist(),
                colorscale=[[0, C["failure"]], [0.5, C["warning"]], [1, C["success"]]],
                cmin=0, cmax=100,
                colorbar=dict(
                    title=dict(text="Éxito %", font=dict(color=C["text"], size=10)),
                    tickfont=dict(color=C["text"], size=9),
                    bgcolor="rgba(0,0,0,0)",
                    bordercolor=C["border"],
                    x=1.01, thickness=14,
                ),
                opacity=0.9,
                line=dict(width=1, color="rgba(255,255,255,0.15)"),
            ),
            customdata=list(zip(
                pad_stats["label"].tolist(),
                pad_stats["total"].tolist(),
                pad_stats["success_rate"].tolist(),
            )),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Lanzamientos: %{customdata[1]}<br>"
                "Tasa éxito: %{customdata[2]:.1f}%"
                "<extra></extra>"
            ),
            showlegend=False,
        ))
        fig.update_geos(
            projection_type="orthographic",
            bgcolor="rgba(6,14,26,1)",
            showland=True,
            landcolor="#162436",
            showocean=True,
            oceancolor="#060e1a",
            showcoastlines=True,
            coastlinecolor=C["border"],
            coastlinewidth=0.7,
            showcountries=True,
            countrycolor=C["border"],
            countrywidth=0.4,
            showframe=False,
            showlakes=True,
            lakecolor="#060e1a",
            showrivers=False,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=C["text"]),
            title=dict(
                text="Globo 3D Interactivo — arrastra para rotar  ·  tamaño = volumen  ·  color = tasa de éxito",
                font=dict(size=12, color=C["muted"]),
            ),
            margin=dict(l=0, r=0, t=40, b=10),
            height=560,
        )
        st.plotly_chart(fig, use_container_width=True, theme=None)

    st.markdown('<div class="sec-title">Estadísticas por País</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if "pad_country_code" in ff.columns:
            cnt = ff["pad_country_code"].value_counts().head(12).reset_index()
            cnt.columns = ["country", "launches"]
            fig = px.bar(cnt, x="launches", y="country", orientation="h",
                         color="launches",
                         color_continuous_scale=[[0, "#023e8a"], [1, "#00b4d8"]])
            fig.update_layout(**layout(
                title=dict(text="Top 12 Países por Lanzamientos", font=dict(size=13)),
                showlegend=False, coloraxis_showscale=False,
            ))
            st.plotly_chart(fig, use_container_width=True, theme=None)

    with c2:
        if "pad_country_code" in ff.columns and "is_success" in ff.columns:
            cs = (
                ff.groupby("pad_country_code")
                .agg(total=("is_success", "count"), success=("is_success", "sum"))
                .reset_index()
            )
            cs["rate"] = (cs["success"] / cs["total"] * 100).round(1)
            cs = cs.nlargest(10, "total")
            fig = px.bar(cs, x="pad_country_code", y="rate",
                         color="rate",
                         color_continuous_scale=[[0, C["failure"]], [0.5, C["warning"]], [1, C["success"]]],
                         range_y=[0, 105])
            fig.update_layout(**layout(
                title=dict(text="Tasa de Éxito por País (Top 10) %", font=dict(size=13)),
                xaxis=dict(title=""), yaxis=dict(title="%"),
                showlegend=False, coloraxis_showscale=False,
            ))
            st.plotly_chart(fig, use_container_width=True, theme=None)

    if "pad_country_code" in ff.columns and "launch_year" in ff.columns:
        st.markdown('<div class="sec-title">Lanzamientos por País a lo Largo del Tiempo</div>', unsafe_allow_html=True)
        top4c = ff["pad_country_code"].value_counts().head(4).index.tolist()
        ctime = (
            ff[ff["pad_country_code"].isin(top4c)]
            .groupby(["launch_year", "pad_country_code"])
            .size()
            .reset_index(name="count")
        )
        fig = go.Figure()
        for i, country in enumerate(top4c):
            cdf = ctime[ctime["pad_country_code"] == country].sort_values("launch_year")
            fig.add_trace(go.Scatter(
                x=cdf["launch_year"].tolist(),
                y=cdf["count"].tolist(),
                name=country, mode="lines",
                line=dict(color=PALETTE[i % len(PALETTE)], width=2),
            ))
        fig.update_layout(**layout(
            title=dict(text="Actividad de Lanzamientos por País — Top 4", font=dict(size=13)),
            xaxis=dict(title="Año"), yaxis=dict(title="Lanzamientos"),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)


# ── Tab 5: SpaceX Rockets ──────────────────────────────────────────────────────

def tab_rockets(rockets_df: pd.DataFrame) -> None:
    if rockets_df.empty:
        st.info("No hay datos de cohetes SpaceX disponibles.")
        return

    st.markdown('<div class="sec-title">Comparativa de Cohetes SpaceX</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        if "rocket_name" in rockets_df.columns and "mass_kg" in rockets_df.columns:
            df_m = rockets_df.dropna(subset=["mass_kg"]).copy()
            df_m["mass_t"] = df_m["mass_kg"] / 1000
            fig = go.Figure()
            for _, row in df_m.iterrows():
                fig.add_trace(go.Bar(
                    name=row.get("rocket_name", "?"),
                    x=["Masa Total (t)"],
                    y=[row["mass_t"]],
                ))
            fig.update_layout(**layout(
                title=dict(text="Masa Total de Cohetes (toneladas)", font=dict(size=13)),
                barmode="group", colorway=PALETTE,
            ))
            st.plotly_chart(fig, use_container_width=True, theme=None)

    with c2:
        # Radar comparison
        if all(c in rockets_df.columns for c in ["rocket_name", "height_meters", "mass_kg", "success_rate_pct"]):
            cats = ["Altura (norm.)", "Masa (norm.)", "Tasa Éxito", "Econom. (inv.)", "Escala"]
            fig = go.Figure()
            for _, row in rockets_df.dropna(subset=["height_meters", "mass_kg"]).iterrows():
                h = min((row.get("height_meters") or 0) / 120, 1)
                m = min((row.get("mass_kg") or 0) / 1_400_000, 1)
                sr = (row.get("success_rate_pct") or 0) / 100
                cost = row.get("cost_per_launch_usd") or 1
                eco = 1 - min(cost / 100_000_000, 1)
                stage = min((row.get("stages") or 1) / 3, 1)
                fig.add_trace(go.Scatterpolar(
                    r=[h, m, sr, eco, stage],
                    theta=cats, fill="toself",
                    name=row.get("rocket_name", "?"),
                    opacity=0.75,
                ))
            fig.update_layout(
                polar=dict(
                    bgcolor="rgba(13,27,42,0.6)",
                    radialaxis=dict(visible=True, range=[0, 1], gridcolor=C["border"],
                                    tickfont=dict(color=C["muted"]), linecolor=C["border"]),
                    angularaxis=dict(gridcolor=C["border"], tickfont=dict(color=C["text"])),
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color=C["text"]),
                legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=C["border"]),
                title=dict(text="Comparativa Normalizada (Radar)", font=dict(size=13, color=C["text"])),
                margin=dict(l=60, r=60, t=55, b=55),
                colorway=PALETTE,
            )
            st.plotly_chart(fig, use_container_width=True, theme=None)

    c3, c4 = st.columns(2)
    with c3:
        if "rocket_name" in rockets_df.columns and "cost_per_launch_usd" in rockets_df.columns:
            df_c = rockets_df.dropna(subset=["cost_per_launch_usd"]).copy()
            df_c["cost_M"] = df_c["cost_per_launch_usd"] / 1_000_000
            _colors = [PALETTE[i % len(PALETTE)] for i in range(len(df_c))]
            fig = go.Figure(go.Bar(
                x=df_c["rocket_name"].tolist(),
                y=df_c["cost_M"].tolist(),
                marker=dict(color=_colors),
                hovertemplate="<b>%{x}</b><br>$%{y:.1f}M<extra></extra>",
            ))
            fig.update_layout(**layout(
                title=dict(text="Costo por Lanzamiento (millones USD)", font=dict(size=13)),
                showlegend=False, xaxis=dict(title=""), yaxis=dict(title="Millones USD"),
            ))
            st.plotly_chart(fig, use_container_width=True, theme=None)

    with c4:
        if "rocket_name" in rockets_df.columns and "height_meters" in rockets_df.columns:
            df_h = rockets_df.dropna(subset=["height_meters"]).copy()
            _colors = [PALETTE[i % len(PALETTE)] for i in range(len(df_h))]
            fig = go.Figure(go.Bar(
                x=df_h["rocket_name"].tolist(),
                y=df_h["height_meters"].tolist(),
                marker=dict(color=_colors),
                hovertemplate="<b>%{x}</b><br>%{y:.0f} m<extra></extra>",
            ))
            fig.update_layout(**layout(
                title=dict(text="Altura de Cohetes (metros)", font=dict(size=13)),
                showlegend=False, xaxis=dict(title=""), yaxis=dict(title="Metros"),
            ))
            st.plotly_chart(fig, use_container_width=True, theme=None)

    st.markdown('<div class="sec-title">Especificaciones Técnicas</div>', unsafe_allow_html=True)
    cols_map = {
        "rocket_name": "Cohete", "height_meters": "Altura (m)", "diameter_meters": "Diámetro (m)",
        "mass_kg": "Masa (kg)", "cost_per_launch_usd": "Costo ($)", "success_rate_pct": "Éxito (%)",
        "first_flight_date": "Primer Vuelo", "stages": "Etapas", "boosters": "Boosters", "is_active": "Activo",
    }
    avail = {k: v for k, v in cols_map.items() if k in rockets_df.columns}
    disp = rockets_df[list(avail.keys())].rename(columns=avail).copy()
    if "Masa (kg)" in disp.columns:
        disp["Masa (kg)"] = disp["Masa (kg)"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "—")
    if "Costo ($)" in disp.columns:
        disp["Costo ($)"] = disp["Costo ($)"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")
    st.dataframe(disp.reset_index(drop=True), use_container_width=True, hide_index=True)


# ── Tab 6: Meteorología ────────────────────────────────────────────────────────

def tab_meteo(ff: pd.DataFrame) -> None:
    wdf = ff.dropna(subset=["temperature_2m_mean", "wind_speed_10m_max"]).copy()
    if wdf.empty:
        st.info("No hay datos meteorológicos suficientes.")
        return

    wdf["outcome"] = wdf["is_success"].map({1: "Éxito", 0: "Fallo"}).fillna("Desconocido")
    colors = {"Éxito": C["success"], "Fallo": C["failure"], "Desconocido": C["muted"]}

    st.markdown('<div class="sec-title">Condiciones al Momento del Lanzamiento</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fig = px.box(wdf, x="outcome", y="temperature_2m_mean", color="outcome",
                     color_discrete_map=colors, points="outliers")
        fig.update_layout(**layout(
            title=dict(text="Temperatura vs Resultado (°C)", font=dict(size=13)),
            showlegend=False, xaxis=dict(title=""), yaxis=dict(title="Temperatura (°C)"),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    with c2:
        fig = px.box(wdf, x="outcome", y="wind_speed_10m_max", color="outcome",
                     color_discrete_map=colors, points="outliers")
        fig.update_layout(**layout(
            title=dict(text="Velocidad de Viento vs Resultado (km/h)", font=dict(size=13)),
            showlegend=False, xaxis=dict(title=""), yaxis=dict(title="Viento máx. (km/h)"),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    c3, c4 = st.columns(2)
    with c3:
        samp = wdf.sample(min(600, len(wdf)), random_state=7)
        fig = go.Figure()
        for outcome, col in colors.items():
            sub = samp[samp["outcome"] == outcome]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["temperature_2m_mean"].tolist(),
                y=sub["wind_speed_10m_max"].tolist(),
                mode="markers", name=outcome,
                marker=dict(color=col, opacity=0.65, size=7),
            ))
        fig.update_layout(**layout(
            title=dict(text="Temperatura vs Viento (muestra)", font=dict(size=13)),
            xaxis=dict(title="Temperatura (°C)"), yaxis=dict(title="Viento (km/h)"),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    with c4:
        fig = go.Figure()
        for outcome, col in colors.items():
            sub = wdf[wdf["outcome"] == outcome]
            if sub.empty:
                continue
            fig.add_trace(go.Histogram(
                x=sub["temperature_2m_mean"].tolist(),
                name=outcome, nbinsx=35, opacity=0.72,
                marker=dict(color=col),
            ))
        fig.update_layout(**layout(
            title=dict(text="Distribución de Temperatura al Lanzamiento", font=dict(size=13)),
            barmode="overlay",
            xaxis=dict(title="Temperatura (°C)"), yaxis=dict(title="Frecuencia"),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    st.markdown('<div class="sec-title">Temperatura Media por Año (en Lanzamientos con Datos)</div>', unsafe_allow_html=True)
    if "launch_year" in wdf.columns:
        yt = wdf.groupby("launch_year").agg(
            temp=("temperature_2m_mean", "mean"),
            wind=("wind_speed_10m_max", "mean"),
        ).reset_index().sort_values("launch_year")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=yt["launch_year"].tolist(), y=yt["temp"].tolist(),
            mode="lines+markers", name="Temp. media (°C)",
            line=dict(color=C["warning"], width=2),
            marker=dict(size=5),
        ))
        fig.add_trace(go.Scatter(
            x=yt["launch_year"].tolist(), y=yt["wind"].tolist(),
            mode="lines+markers", name="Viento medio (km/h)",
            line=dict(color=C["accent"], width=2),
            marker=dict(size=5), yaxis="y2",
        ))
        fig.update_layout(**layout(
            title=dict(text="Temperatura y Viento Promedio por Año", font=dict(size=13)),
            xaxis=dict(title="Año"),
            yaxis=dict(title="Temperatura (°C)", color=C["warning"]),
            yaxis2=dict(title="Viento (km/h)", color=C["accent"],
                        overlaying="y", side="right", showgrid=False),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)


# ── Tab 7: Galería ────────────────────────────────────────────────────────────

def tab_galeria(img_df: pd.DataFrame) -> None:
    if img_df.empty:
        st.info("No se encontraron imágenes. Asegúrate de que la ingesta se haya ejecutado.")
        return

    st.markdown('<div class="sec-title">Galería de Lanzamientos</div>', unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns([1, 1, 2])
    with fc1:
        src_opts = ["Todas"] + sorted(img_df["source"].dropna().unique().tolist())
        sel_src = st.selectbox("Fuente", src_opts, key="gal_src",
                               format_func=lambda s: s.replace("_", " ").title() if s != "Todas" else s)
    with fc2:
        if "launch_year" in img_df.columns:
            yrs_g = sorted(img_df["launch_year"].dropna().astype(int).unique().tolist(), reverse=True)
            sel_yr = st.selectbox("Año", ["Todos"] + [str(y) for y in yrs_g], key="gal_yr")
        else:
            sel_yr = "Todos"
    with fc3:
        search = st.text_input("Buscar misión", "", key="gal_search", placeholder="ej. Falcon 9, Ariane 5…")

    filt = img_df.copy()
    if sel_src != "Todas":
        filt = filt[filt["source"] == sel_src]
    if sel_yr != "Todos" and "launch_year" in filt.columns:
        filt = filt[filt["launch_year"].astype(int) == int(sel_yr)]
    if search and "launch_name" in filt.columns:
        filt = filt[filt["launch_name"].str.contains(search, case=False, na=False)]
    filt = filt.dropna(subset=["image_url"])

    total = len(filt)
    if total == 0:
        st.info("Sin imágenes para los filtros seleccionados.")
        return

    page_size = 20
    total_pages = max(1, (total - 1) // page_size + 1)
    pa, pb = st.columns([5, 1])
    with pa:
        st.caption(f"{total:,} imágenes encontradas")
    with pb:
        page = int(st.number_input("Página", min_value=1, max_value=total_pages,
                                   value=1, step=1, key="gal_page")) - 1

    page_df = filt.iloc[page * page_size: (page + 1) * page_size]

    cells = ""
    for _, row in page_df.iterrows():
        url = str(row.get("image_url", ""))
        name = str(row.get("launch_name", "") or "—")
        yr_tag = f" · {int(row['launch_year'])}" if "launch_year" in row and pd.notna(row.get("launch_year")) else ""
        src_tag = str(row.get("source", "")).replace("_", " ").title()
        cells += (
            f'<div style="border-radius:8px;overflow:hidden;background:{C["card"]};border:1px solid {C["border"]};">'
            f'<img src="{url}" loading="lazy" '
            f'style="width:100%;height:155px;object-fit:cover;display:block;" '
            f'onerror="this.parentElement.style.display=\'none\'">'
            f'<div style="padding:0.35rem 0.5rem;">'
            f'<div style="font-size:0.7rem;color:{C["text"]};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="{name}">{name}{yr_tag}</div>'
            f'<div style="font-size:0.62rem;color:{C["muted"]};">{src_tag}</div>'
            f'</div></div>'
        )
    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.65rem;margin-top:0.5rem;">{cells}</div>',
        unsafe_allow_html=True,
    )
    # Spacer so the grid doesn't get clipped by the bottom of the tab
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)


# ── Tab 9: Simulador ──────────────────────────────────────────────────────────

def _launch_probability(rocket_name: str, temperature: float, wind_speed: float,
                        rockets_df: pd.DataFrame) -> float:
    """Heuristic success probability = rocket base rate × temperature factor × wind factor."""
    base = 0.82
    if not rockets_df.empty and "rocket_name" in rockets_df.columns and "success_rate_pct" in rockets_df.columns:
        row = rockets_df[rockets_df["rocket_name"] == rocket_name]
        if not row.empty:
            val = row["success_rate_pct"].iloc[0]
            if pd.notna(val):
                base = float(val) / 100

    if 10 <= temperature <= 28:
        temp_f = 1.0
    elif temperature < 10:
        temp_f = max(0.55, 1.0 - abs(temperature - 10) * 0.025)
    else:
        temp_f = max(0.65, 1.0 - (temperature - 28) * 0.018)

    if wind_speed <= 30:
        wind_f = 1.0
    elif wind_speed <= 60:
        wind_f = 1.0 - (wind_speed - 30) / 30 * 0.40
    else:
        wind_f = max(0.05, 0.60 - (wind_speed - 60) / 60 * 0.55)

    return min(0.99, max(0.01, base * temp_f * wind_f))


def tab_simulador(rockets_df: pd.DataFrame) -> None:
    st.markdown('<div class="sec-title">Configura tu Lanzamiento</div>', unsafe_allow_html=True)

    rocket_names = (
        rockets_df["rocket_name"].dropna().tolist()
        if not rockets_df.empty and "rocket_name" in rockets_df.columns
        else ["Falcon 9", "Falcon Heavy", "Starship", "Falcon 1"]
    )

    col_l, col_r = st.columns([1, 1.6], gap="large")

    with col_l:
        selected = st.selectbox("🚀 Cohete", rocket_names, key="sim_rocket")
        temp = st.slider("🌡️ Temperatura (°C)", -20, 50, 22, key="sim_temp")
        wind = st.slider("💨 Velocidad del viento (km/h)", 0, 120, 10, key="sim_wind")

        # Rocket info card
        if not rockets_df.empty and "rocket_name" in rockets_df.columns:
            rrow_df = rockets_df[rockets_df["rocket_name"] == selected]
            if not rrow_df.empty:
                rrow = rrow_df.iloc[0]
                lines = []
                if pd.notna(rrow.get("height_meters")):
                    lines.append(f"📏 Altura: {rrow['height_meters']:.0f} m")
                if pd.notna(rrow.get("mass_kg")):
                    lines.append(f"⚖️ Masa: {rrow['mass_kg']/1000:.0f} t")
                if pd.notna(rrow.get("success_rate_pct")):
                    lines.append(f"📊 Tasa histórica: {rrow['success_rate_pct']:.0f}%")
                if pd.notna(rrow.get("cost_per_launch_usd")):
                    lines.append(f"💰 Costo: ${rrow['cost_per_launch_usd']/1e6:.0f}M")
                if lines:
                    st.markdown(
                        f'<div style="background:{C["card2"]};border:1px solid {C["border"]};'
                        f'border-radius:10px;padding:0.85rem 1rem;margin-top:0.75rem;">'
                        + "".join(
                            f'<div style="color:{C["text"]};font-size:0.83rem;margin:0.2rem 0;">{l}</div>'
                            for l in lines
                        )
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                if pd.notna(rrow.get("description")):
                    desc = str(rrow["description"])
                    st.caption(desc[:240] + "…" if len(desc) > 240 else desc)

        img_url = _rocket_image(selected)
        if img_url:
            st.image(img_url, use_column_width=True)

    with col_r:
        prob = _launch_probability(selected, temp, wind, rockets_df)
        prob_pct = round(prob * 100, 1)

        if prob_pct >= 80:
            gc = C["success"]; label = "Condiciones óptimas para el lanzamiento"; icon = "✅"
        elif prob_pct >= 60:
            gc = C["warning"]; label = "Condiciones aceptables — proceder con precaución"; icon = "⚠️"
        elif prob_pct >= 40:
            gc = C["warning"]; label = "Condiciones desfavorables — riesgo elevado"; icon = "🔶"
        else:
            gc = C["failure"]; label = "Condiciones peligrosas — lanzamiento no recomendado"; icon = "🚫"

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=prob_pct,
            number=dict(suffix="%", font=dict(color=gc, size=56, family="Orbitron, sans-serif")),
            gauge=dict(
                axis=dict(range=[0, 100], tickwidth=1,
                          tickcolor=C["muted"], tickfont=dict(color=C["muted"], size=10)),
                bar=dict(color=gc, thickness=0.72),
                bgcolor="rgba(13,27,42,0.8)",
                bordercolor=C["border"],
                borderwidth=2,
                steps=[
                    dict(range=[0, 40],  color="rgba(248,113,113,0.18)"),
                    dict(range=[40, 70], color="rgba(251,146,60,0.14)"),
                    dict(range=[70, 100], color="rgba(74,222,128,0.12)"),
                ],
                threshold=dict(line=dict(color="white", width=2), thickness=0.8, value=prob_pct),
            ),
            title=dict(text="Probabilidad de Éxito", font=dict(color=C["muted"], size=13, family="Inter")),
        ))
        fig.update_layout(
            template="none",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=C["text"]),
            height=340,
            margin=dict(l=30, r=30, t=55, b=10),
        )
        st.plotly_chart(fig, use_container_width=True, theme=None)

        st.markdown(
            f'<div style="text-align:center;padding:1.25rem 1.5rem;'
            f'background:rgba(0,0,0,0.25);border-radius:14px;'
            f'border:1px solid {gc}55;margin-top:0.25rem;">'
            f'<div style="font-size:2rem;margin-bottom:0.35rem;">{icon}</div>'
            f'<div style="color:{gc};font-size:1.05rem;font-weight:600;">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Factor breakdown ──
        st.markdown('<div class="sec-title" style="margin-top:1.5rem;">Desglose de Factores</div>',
                    unsafe_allow_html=True)

        base_r = 0.82
        if not rockets_df.empty and "rocket_name" in rockets_df.columns and "success_rate_pct" in rockets_df.columns:
            rr = rockets_df[rockets_df["rocket_name"] == selected]
            if not rr.empty and pd.notna(rr["success_rate_pct"].iloc[0]):
                base_r = float(rr["success_rate_pct"].iloc[0]) / 100

        if 10 <= temp <= 28:
            temp_f = 1.0
        elif temp < 10:
            temp_f = max(0.55, 1.0 - abs(temp - 10) * 0.025)
        else:
            temp_f = max(0.65, 1.0 - (temp - 28) * 0.018)

        if wind <= 30:
            wind_f = 1.0
        elif wind <= 60:
            wind_f = 1.0 - (wind - 30) / 30 * 0.40
        else:
            wind_f = max(0.05, 0.60 - (wind - 60) / 60 * 0.55)

        factor_labels = [
            f"Cohete ({selected})",
            f"Temperatura ({temp}°C)",
            f"Viento ({wind} km/h)",
        ]
        factor_vals = [base_r * 100, temp_f * 100, wind_f * 100]
        factor_colors = [
            C["accent"],
            C["success"] if temp_f >= 0.95 else (C["warning"] if temp_f >= 0.75 else C["failure"]),
            C["success"] if wind_f >= 0.95 else (C["warning"] if wind_f >= 0.65 else C["failure"]),
        ]
        fig2 = go.Figure(go.Bar(
            x=factor_vals,
            y=factor_labels,
            orientation="h",
            marker=dict(color=factor_colors, opacity=0.88),
            text=[f"{v:.0f}%" for v in factor_vals],
            textposition="outside",
            textfont=dict(color=C["text"], size=12),
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        ))
        fig2.update_layout(
            template="none",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(13,27,42,0.6)",
            font=dict(color=C["text"], family="Inter, sans-serif", size=11),
            xaxis=dict(range=[0, 118], showgrid=True, gridcolor=C["border"],
                       zeroline=False, tickcolor=C["muted"], ticksuffix="%"),
            yaxis=dict(showgrid=False, zeroline=False, tickcolor=C["muted"]),
            height=180,
            margin=dict(l=10, r=60, t=10, b=10),
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True, theme=None)


# ── Tab 9: Costos ─────────────────────────────────────────────────────────────

def tab_costos(costs_df: pd.DataFrame) -> None:
    if costs_df.empty or "estimated_cost_usd" not in costs_df.columns:
        st.info("No se encontraron datos de costes. Asegúrate de que `dashboard/data/costs.parquet` existe.")
        return

    df = costs_df.dropna(subset=["estimated_cost_usd"]).copy()

    # ── KPIs ──
    total_inv = df["estimated_cost_usd"].sum()
    avg_cost = df["estimated_cost_usd"].mean()
    n_launches = len(df)
    n_providers = df["provider_name"].nunique() if "provider_name" in df.columns else 0
    success_mask = df["is_success"] == 1 if "is_success" in df.columns else pd.Series([True] * len(df))
    cost_success = df.loc[success_mask, "estimated_cost_usd"].mean() if success_mask.any() else np.nan

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Inversión Total Estimada", f"${total_inv/1e9:.1f}B")
    k2.metric("Coste Promedio/Lanzamiento", f"${avg_cost/1e6:.1f}M")
    k3.metric("Coste Medio en Éxitos", f"${cost_success/1e6:.1f}M" if not np.isnan(cost_success) else "—")
    k4.metric("Lanzamientos Analizados", f"{n_launches:,}")
    k5.metric("Proveedores", str(n_providers))

    st.markdown("---")

    # ── Fila 1: Coste por proveedor + Evolución temporal ──
    st.markdown('<div class="sec-title">Coste Promedio por Proveedor y Evolución Temporal</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        prov_avg = (
            df.groupby("provider_name")["estimated_cost_usd"]
            .mean()
            .sort_values(ascending=True)
            .reset_index()
        )
        fig = go.Figure(go.Bar(
            x=(prov_avg["estimated_cost_usd"] / 1e6).round(1).tolist(),
            y=prov_avg["provider_name"].tolist(),
            orientation="h",
            marker=dict(
                color=(prov_avg["estimated_cost_usd"] / 1e6).tolist(),
                colorscale=[[0, C["success"]], [0.5, C["accent"]], [1, C["warning"]]],
                showscale=False,
            ),
            text=[f"${v:.0f}M" for v in (prov_avg["estimated_cost_usd"] / 1e6)],
            textposition="outside",
        ))
        fig.update_layout(**layout(
            title=dict(text="Coste Promedio por Lanzamiento (USD M)", font=dict(size=13)),
            xaxis=dict(title="Millones USD"),
            yaxis=dict(title=""),
            margin=dict(l=150, r=60, t=45, b=40),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    with c2:
        top5 = (
            df.groupby("provider_name")["estimated_cost_usd"]
            .mean()
            .nlargest(5)
            .index.tolist()
        )
        yearly_prov = (
            df[df["provider_name"].isin(top5)]
            .groupby(["launch_year", "provider_name"])["estimated_cost_usd"]
            .mean()
            .reset_index()
            .sort_values("launch_year")
        )
        fig = go.Figure()
        for i, prov in enumerate(top5):
            sub = yearly_prov[yearly_prov["provider_name"] == prov]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["launch_year"].tolist(),
                y=(sub["estimated_cost_usd"] / 1e6).round(1).tolist(),
                mode="lines+markers",
                name=prov,
                line=dict(color=PALETTE[i % len(PALETTE)], width=2),
                marker=dict(size=5),
            ))
        fig.update_layout(**layout(
            title=dict(text="Evolución del Coste — Top 5 Proveedores (USD M)", font=dict(size=13)),
            xaxis=dict(title="Año"),
            yaxis=dict(title="Coste Promedio (M USD)"),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    # ── Fila 2: Inversión total por año + Coste vs Tasa de éxito ──
    st.markdown('<div class="sec-title">Inversión Total por Año y Relación Coste–Éxito</div>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)

    with c3:
        yearly_inv = (
            df.groupby("launch_year")["estimated_cost_usd"]
            .sum()
            .reset_index()
            .sort_values("launch_year")
        )
        fig = go.Figure(go.Bar(
            x=yearly_inv["launch_year"].astype(int).tolist(),
            y=(yearly_inv["estimated_cost_usd"] / 1e9).round(3).tolist(),
            marker=dict(color=C["accent"], opacity=0.85),
            text=[(f"${v:.2f}B") for v in (yearly_inv["estimated_cost_usd"] / 1e9)],
            textposition="outside",
        ))
        fig.update_layout(**layout(
            title=dict(text="Inversión Total Estimada por Año (USD B)", font=dict(size=13)),
            xaxis=dict(title="Año", dtick=2),
            yaxis=dict(title="Miles de Millones USD"),
        ))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    with c4:
        if "is_success" in df.columns:
            prov_stats = (
                df.groupby("provider_name")
                .agg(
                    avg_cost=("estimated_cost_usd", "mean"),
                    success_rate=("is_success", "mean"),
                    n=("estimated_cost_usd", "count"),
                )
                .reset_index()
            )
            prov_stats["success_pct"] = (prov_stats["success_rate"] * 100).round(1)
            fig = go.Figure()
            for i, row in prov_stats.iterrows():
                fig.add_trace(go.Scatter(
                    x=[row["avg_cost"] / 1e6],
                    y=[row["success_pct"]],
                    mode="markers+text",
                    name=row["provider_name"],
                    marker=dict(
                        size=max(10, min(40, row["n"] / 5)),
                        color=PALETTE[i % len(PALETTE)],
                        opacity=0.85,
                        line=dict(color="white", width=1),
                    ),
                    text=[row["provider_name"].split()[0]],
                    textposition="top center",
                    textfont=dict(size=9),
                    showlegend=False,
                ))
            fig.update_layout(**layout(
                title=dict(text="Coste Promedio vs Tasa de Éxito por Proveedor", font=dict(size=13)),
                xaxis=dict(title="Coste Promedio (M USD)"),
                yaxis=dict(title="Tasa de Éxito (%)"),
            ))
            st.plotly_chart(fig, use_container_width=True, theme=None)
        else:
            st.info("Sin datos de éxito disponibles.")

    # ── Fila 3: Distribución por categoría + Coste por tipo de misión ──
    st.markdown('<div class="sec-title">Distribución por Categoría y Tipo de Misión</div>', unsafe_allow_html=True)
    c5, c6 = st.columns(2)

    with c5:
        if "cost_category" in df.columns:
            cat_data = (
                df.groupby("cost_category")["estimated_cost_usd"]
                .agg(["count", "mean"])
                .reset_index()
                .rename(columns={"count": "lanzamientos", "mean": "avg_cost"})
            )
            cat_colors = {"Budget": C["success"], "Standard": C["accent"],
                          "Premium": C["warning"], "Heavy": C["failure"]}
            fig = go.Figure(go.Pie(
                labels=cat_data["cost_category"].tolist(),
                values=cat_data["lanzamientos"].tolist(),
                hole=0.45,
                marker=dict(colors=[cat_colors.get(c, C["muted"]) for c in cat_data["cost_category"]]),
                textinfo="label+percent",
                textfont=dict(size=11),
            ))
            fig.update_layout(**layout(
                title=dict(text="Lanzamientos por Categoría de Coste", font=dict(size=13)),
                showlegend=True,
                margin=dict(l=20, r=20, t=45, b=20),
            ))
            st.plotly_chart(fig, use_container_width=True, theme=None)
        else:
            st.info("Sin datos de categoría.")

    with c6:
        if "mission_type" in df.columns:
            mission_cost = (
                df.groupby("mission_type")["estimated_cost_usd"]
                .mean()
                .sort_values(ascending=False)
                .reset_index()
            )
            fig = go.Figure(go.Bar(
                x=mission_cost["mission_type"].tolist(),
                y=(mission_cost["estimated_cost_usd"] / 1e6).round(1).tolist(),
                marker=dict(
                    color=(mission_cost["estimated_cost_usd"] / 1e6).tolist(),
                    colorscale=[[0, C["accent"]], [1, C["warning"]]],
                    showscale=False,
                ),
            ))
            fig.update_layout(**layout(
                title=dict(text="Coste Promedio por Tipo de Misión (USD M)", font=dict(size=13)),
                xaxis=dict(title="", tickangle=-30),
                yaxis=dict(title="M USD"),
            ))
            st.plotly_chart(fig, use_container_width=True, theme=None)
        else:
            st.info("Sin datos de tipo de misión.")


# ── Tab 10: Asistente IA ──────────────────────────────────────────────────────

def _build_chat_context(
    costs_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    features_df: pd.DataFrame,
    rockets_df: pd.DataFrame,
) -> str:
    lines: list[str] = ["# Space Launches — Datos del Dashboard\n"]

    if not metrics_df.empty and "total_launches" in metrics_df.columns:
        yr_min = int(metrics_df["launch_year"].min())
        yr_max = int(metrics_df["launch_year"].max())
        total = int(metrics_df["total_launches"].sum())
        lines += [
            "## Resumen general",
            f"- Periodo: {yr_min}–{yr_max}",
            f"- Total lanzamientos: {total:,}",
        ]
        if "successful_launches" in metrics_df.columns:
            succ = int(metrics_df["successful_launches"].sum())
            lines.append(f"- Exitosos: {succ:,} ({succ/max(total,1)*100:.1f}%)")
        lines.append("")

    if not metrics_df.empty and "provider_name" in metrics_df.columns:
        top = (
            metrics_df.groupby("provider_name")["total_launches"]
            .sum().nlargest(10).reset_index()
        )
        lines.append("## Top 10 proveedores")
        for _, row in top.iterrows():
            pn = row["provider_name"]
            n = int(row["total_launches"])
            sr_rows = metrics_df[metrics_df["provider_name"] == pn]
            if "success_rate_pct" in sr_rows.columns:
                sr = sr_rows["success_rate_pct"].mean()
                lines.append(f"- {pn}: {n} lanzamientos, tasa éxito {sr:.1f}%")
            else:
                lines.append(f"- {pn}: {n} lanzamientos")
        lines.append("")

    if not costs_df.empty and "estimated_cost_usd" in costs_df.columns:
        total_inv = costs_df["estimated_cost_usd"].sum() / 1e9
        avg_cost = costs_df["estimated_cost_usd"].mean() / 1e6
        lines += [
            "## Costes de lanzamiento (estimados)",
            f"- Inversión total: ${total_inv:.1f}B USD",
            f"- Coste promedio: ${avg_cost:.1f}M USD/lanzamiento",
        ]
        if "cost_category" in costs_df.columns:
            cats = costs_df["cost_category"].value_counts()
            lines.append("- Categorías: " + ", ".join(f"{k}={v}" for k, v in cats.items()))
        if "provider_name" in costs_df.columns:
            prov_avg = (
                costs_df.groupby("provider_name")["estimated_cost_usd"]
                .mean().sort_values(ascending=False)
            )
            lines.append("- Coste medio por proveedor:")
            for prov, cost in prov_avg.items():
                lines.append(f"  - {prov}: ${cost/1e6:.1f}M")
        if "rocket_name" in costs_df.columns:
            rkt_top = costs_df.groupby("rocket_name")["estimated_cost_usd"].mean().nlargest(8)
            lines.append("- Cohetes más caros:")
            for rkt, cost in rkt_top.items():
                lines.append(f"  - {rkt}: ${cost/1e6:.1f}M")
        lines.append("")

    if not features_df.empty:
        if "mission_type" in features_df.columns:
            mt = features_df["mission_type"].value_counts().head(10)
            lines.append("## Tipos de misión")
            for k, v in mt.items():
                lines.append(f"- {k}: {v}")
            lines.append("")
        if "mission_orbit" in features_df.columns:
            orb = features_df["mission_orbit"].value_counts().head(8)
            lines.append("## Órbitas")
            for k, v in orb.items():
                lines.append(f"- {k}: {v}")
            lines.append("")
        if "pad_country_code" in features_df.columns:
            countries = features_df["pad_country_code"].value_counts().head(8)
            lines.append("## Países con más lanzamientos")
            for k, v in countries.items():
                lines.append(f"- {k}: {v}")
            lines.append("")
        if "rocket_name" in features_df.columns:
            rkt = features_df["rocket_name"].value_counts().head(10)
            lines.append("## Cohetes más usados")
            for k, v in rkt.items():
                lines.append(f"- {k}: {v} lanzamientos")
            lines.append("")

    if not rockets_df.empty:
        lines.append("## Cohetes SpaceX (API oficial)")
        for _, row in rockets_df.iterrows():
            name = row.get("rocket_name", "?")
            status = "Activo" if row.get("is_active") else "Inactivo"
            cost_val = row.get("cost_per_launch_usd")
            cost_str = f"${float(cost_val)/1e6:.0f}M" if pd.notna(cost_val) else "N/D"
            sr_val = row.get("success_rate_pct")
            sr_str = f"{float(sr_val):.0f}%" if pd.notna(sr_val) else "N/D"
            h_val = row.get("height_meters")
            h_str = f"{float(h_val):.0f}m" if pd.notna(h_val) else "N/D"
            m_val = row.get("mass_kg")
            m_str = f"{float(m_val)/1000:.0f}t" if pd.notna(m_val) else "N/D"
            first = row.get("first_flight_date", "N/D")
            desc = str(row.get("description") or "")
            lines.append(f"### {name}")
            lines.append(f"- Estado: {status} | Coste: {cost_str} | Éxito: {sr_str} | Altura: {h_str} | Masa: {m_str} | Primer vuelo: {first}")
            if desc:
                lines.append(f"- {desc[:300]}{'...' if len(desc)>300 else ''}")
        lines.append("")

    return "\n".join(lines)


def tab_asistente(
    costs_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    features_df: pd.DataFrame,
    rockets_df: pd.DataFrame,
) -> None:
    import httpx
    import json as _json

    api_key: str = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error("Falta `GROQ_API_KEY` en `.streamlit/secrets.toml`.")
        return

    st.markdown('<div class="sec-title">Asistente IA — Space Launches</div>', unsafe_allow_html=True)

    with st.expander("ℹ️ ¿Sobre qué puedo preguntarme?", expanded=False):
        st.markdown("""
**Datos del dashboard:** lanzamientos por año, proveedores, tasas de éxito, costes estimados, tipos de misión, órbitas, países.

**SpaceX:** detalles técnicos de Falcon 9, Falcon Heavy, Starship, Dragon, etc.

**General:** física orbital, historia espacial, agencias (NASA, ESA, Roscosmos…), cohetes de otras empresas, astronomía.
        """)

    col_btn, _ = st.columns([1, 5])
    with col_btn:
        if st.button("🗑️ Limpiar chat", use_container_width=True):
            st.session_state["chat_messages"] = []
            st.rerun()

    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    if "chat_data_context" not in st.session_state:
        st.session_state["chat_data_context"] = _build_chat_context(
            costs_df, metrics_df, features_df, rockets_df
        )

    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    with st.form(key="chat_form", clear_on_submit=True):
        col_in, col_btn2 = st.columns([6, 1])
        with col_in:
            user_input = st.text_input(
                "", placeholder="Pregunta sobre lanzamientos espaciales…",
                label_visibility="collapsed",
            )
        with col_btn2:
            submitted = st.form_submit_button("Enviar ➤", use_container_width=True)

    prompt = user_input.strip() if submitted and user_input.strip() else None
    if not prompt:
        return

    st.session_state["chat_messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    system_text = (
        "Eres un asistente experto en astronáutica y exploración espacial. "
        "Respondes siempre en español, de forma clara, precisa y amigable. "
        "Cuando te pregunten sobre los datos del dashboard, usa únicamente la información "
        "proporcionada a continuación. Para preguntas generales sobre espacio, "
        "física orbital o historia espacial usa tu conocimiento general.\n\n"
        + st.session_state["chat_data_context"]
    )

    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state["chat_messages"]
    ]

    # Groq — modelos gratuitos en orden de preferencia
    _MODELS = [
        "llama-3.3-70b-versatile",   # mejor calidad
        "llama-3.1-8b-instant",      # más rápido, fallback
    ]
    _GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

    def _call_model(model: str):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system_text}, *messages],
            "stream": True,
            "max_tokens": 1024,
        }
        with httpx.stream("POST", _GROQ_URL, headers=headers, json=body, timeout=60.0) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    return
                try:
                    chunk = _json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content") or ""
                    if delta:
                        yield delta
                except (ValueError, KeyError, IndexError):
                    pass

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        success = False
        for model in _MODELS:
            try:
                full_response = ""
                for token in _call_model(model):
                    full_response += token
                    placeholder.markdown(full_response + "▌")
                placeholder.markdown(full_response)
                success = True
                break
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code
                if code == 429:
                    import time as _time
                    placeholder.info(f"⏳ Rate limit en `{model}`, probando fallback…")
                    _time.sleep(3)
                    continue
                placeholder.error(f"Error HTTP {code} en `{model}`.")
                return
            except Exception as exc:
                placeholder.error(f"Error de API: {exc}")
                return
        if not success:
            placeholder.warning("Límite de peticiones alcanzado. Espera unos segundos e inténtalo de nuevo.")
            return

    st.session_state["chat_messages"].append({"role": "assistant", "content": full_response})


# ── Tabla final ────────────────────────────────────────────────────────────────

def render_table(ff: pd.DataFrame) -> None:
    st.markdown('<div class="sec-title">Explorador de Lanzamientos</div>', unsafe_allow_html=True)
    cols_map = {
        "launch_name": "Misión", "launch_year": "Año",
        "provider_name": "Agencia", "rocket_name": "Cohete",
        "mission_type": "Tipo Misión", "mission_orbit": "Órbita",
        "pad_country_code": "País", "is_success": "Resultado",
        "temperature_2m_mean": "Temp (°C)", "wind_speed_10m_max": "Viento (km/h)",
        "launch_image_count": "Imágenes",
    }
    avail = {k: v for k, v in cols_map.items() if k in ff.columns}
    disp = ff[list(avail.keys())].rename(columns=avail).copy()
    if "Resultado" in disp.columns:
        disp["Resultado"] = disp["Resultado"].map({1: "✓ Éxito", 0: "✗ Fallo"}).fillna("?")
    for nc in ("Temp (°C)", "Viento (km/h)"):
        if nc in disp.columns:
            disp[nc] = disp[nc].round(1)
    st.dataframe(
        disp.sort_values("Año", ascending=False).reset_index(drop=True),
        use_container_width=True, hide_index=True,
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Space Launches — Dashboard",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()

    with st.spinner("Cargando datos del universo…"):
        mf_all = load_metrics()
        ff_all = load_features()
        rockets_df = load_rockets()
        raw_df = load_raw_jsonl()
        img_df = load_images()
        costs_df = load_costs()

    if mf_all.empty:
        st.error("No se encontraron datos en `data/gold/`. Ejecuta primero el pipeline de procesamiento.")
        return

    # ── Enrich features: merge raw (200 records) + gold weather (59 records) ──
    if not raw_df.empty:
        enrich = raw_df.copy()
        # Only pull weather/image cols from gold — pad coords already exist in raw_df
        w_cols = [c for c in ["launch_id", "temperature_2m_mean", "wind_speed_10m_max",
                               "launch_image_count"]
                  if c in ff_all.columns]
        if w_cols and "launch_id" in enrich.columns:
            weather_only = ff_all[w_cols].dropna(subset=["launch_id"])
            for col in ("temperature_2m_mean", "wind_speed_10m_max"):
                if col in enrich.columns:
                    enrich = enrich.drop(columns=[col])
            enrich = enrich.merge(weather_only, on="launch_id", how="left")
        ff_all = enrich

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("### SPACE LAUNCHES\n#### Data & ML Platform")
        st.markdown("---")
        st.markdown("### Filtros")

        all_years = sorted(mf_all["launch_year"].unique())
        y0, y1 = int(min(all_years)), int(max(all_years))
        year_range = st.slider("Rango de años", y0, y1, (y0, y1))

        all_provs = sorted(mf_all["provider_name"].dropna().unique())
        sel_provs = st.multiselect("Agencias", options=all_provs, default=all_provs[:],
                                   placeholder="Todas las agencias")

        orbit_opts: list[str] = []
        if "mission_orbit" in ff_all.columns:
            orbit_opts = sorted(ff_all["mission_orbit"].dropna().unique())
        sel_orbits = st.multiselect("Órbitas", options=orbit_opts, default=orbit_opts[:])

        st.markdown("---")
        st.markdown("### Fuentes")
        st.markdown("""
- 🛸 Launch Library 2
- 🚀 SpaceX API v5
- 🌤️ Open-Meteo Archive
        """)
        st.markdown("---")
        st.metric("Registros gold", f"{len(ff_all):,}")

    # ── Apply filters ──
    mf = mf_all.copy()
    mf = mf[(mf["launch_year"] >= year_range[0]) & (mf["launch_year"] <= year_range[1])]
    if sel_provs:
        mf = mf[mf["provider_name"].isin(sel_provs)]

    ff = ff_all.copy()
    ff = ff[(ff["launch_year"] >= year_range[0]) & (ff["launch_year"] <= year_range[1])]
    if sel_provs and "provider_name" in ff.columns:
        ff = ff[ff["provider_name"].isin(sel_provs)]
    if sel_orbits and "mission_orbit" in ff.columns:
        ff = ff[ff["mission_orbit"].isin(sel_orbits)]

    if mf.empty:
        st.warning("Sin datos para los filtros seleccionados.")
        return

    # ── Hero ──
    total = int(mf["total_launches"].sum())
    succ = int(mf["successful_launches"].sum()) if "successful_launches" in mf.columns else 0
    rate = round(succ / total * 100, 1) if total else 0.0
    n_years = year_range[1] - year_range[0] + 1
    provs_n = mf["provider_name"].nunique()
    render_hero(total, rate, n_years, provs_n)

    # ── KPIs ──
    render_kpis(mf, ff)
    st.markdown("---")

    # ── Tabs ──
    t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 = st.tabs([
        "📈 Histórico",
        "🏢 Proveedores",
        "🛸 Misiones & Órbitas",
        "🌍 Geografía",
        "🚀 SpaceX Rockets",
        "🌤️ Meteorología",
        "🖼️ Galería",
        "🎮 Simulador",
        "💰 Costos de Lanzamiento",
        "🤖 Asistente IA",
    ])
    with t1:
        tab_historico(mf, ff)
    with t2:
        tab_proveedores(mf)
    with t3:
        tab_misiones(ff, raw_df)
    with t4:
        tab_geografia(ff)
    with t5:
        tab_rockets(rockets_df)
    with t6:
        tab_meteo(ff)
    with t7:
        tab_galeria(img_df)
    with t8:
        tab_simulador(rockets_df)
    with t9:
        tab_costos(costs_df)
    with t10:
        tab_asistente(costs_df, mf_all, ff_all, rockets_df)

    st.markdown("---")
    render_table(ff)


if __name__ == "__main__":
    main()
