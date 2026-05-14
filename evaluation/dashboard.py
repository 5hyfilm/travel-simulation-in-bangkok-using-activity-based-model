"""
evaluation/dashboard.py
=======================
Interactive HTML validation dashboard for the Bangkok MATSim simulation.
Produces a self-contained  evaluation/validation_dashboard.html.

Run from project root:
    python evaluation/dashboard.py

Works with or without a Google Maps API key:
  - With key   : full validation (sim vs Google Maps scatter, heatmap, errors)
  - Without key: simulation-only view (coverage + travel time distribution)
"""

import os, json, math, datetime
import numpy as np
import pandas as pd
from pyproj import Transformer

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.io as pio
except ImportError:
    raise ImportError("plotly is required.  Run:  pip install plotly")

# ── Paths & config ────────────────────────────────────────────────────────────
_ROOT      = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_CFG_PATH  = os.path.join(_ROOT, "config.json")
TRIPS_FILE = os.path.join(_ROOT, "normal_output", "output", "output_trips.csv.gz")
OUT_HTML   = os.path.join(os.path.dirname(__file__), "validation_dashboard.html")

GOOGLE_MAPS_API_KEY = "YOUR_API_KEY_HERE"
if os.path.exists(_CFG_PATH):
    with open(_CFG_PATH, encoding="utf-8") as _f:
        _cfg = json.load(_f)
    GOOGLE_MAPS_API_KEY = _cfg.get("api_keys", {}).get("google_maps", "YOUR_API_KEY_HERE")

MIN_AGENTS       = 10
MAX_DIST_KM      = 60
MIN_DIST_KM      = 1.5
SEARCH_RADIUS_KM = 3.0

QUERY_HOURS = {
    "AM peak (07:00)": 7,
    "Midday (12:00)":  12,
    "PM peak (17:00)": 17,
}

ROUTES = [
    ("Silom → Chatuchak",            13.7221, 100.5296, 13.8030, 100.5530),
    ("Chatuchak → Silom",            13.8030, 100.5530, 13.7221, 100.5296),
    ("Silom → Sukhumvit Asok",       13.7221, 100.5296, 13.7374, 100.5608),
    ("Sukhumvit Asok → Silom",       13.7374, 100.5608, 13.7221, 100.5296),
    ("Silom → Victory Monument",     13.7221, 100.5296, 13.7649, 100.5374),
    ("Victory Monument → Silom",     13.7649, 100.5374, 13.7221, 100.5296),
    ("Charoennakorn → Victory Mon",  13.7201, 100.5072, 13.7649, 100.5374),
    ("Don Mueang → Silom",           13.9126, 100.6069, 13.7221, 100.5296),
    ("Chatuchak → Don Mueang",       13.8030, 100.5530, 13.9126, 100.6069),
    ("Don Mueang → Chatuchak",       13.9126, 100.6069, 13.8030, 100.5530),
    ("Bang Khen → Chatuchak",        13.8700, 100.5900, 13.8030, 100.5530),
    ("Chatuchak → Bang Khen",        13.8030, 100.5530, 13.8700, 100.5900),
    ("Ratchada → Victory Monument",  13.7670, 100.5700, 13.7649, 100.5374),
    ("Victory Monument → Ratchada",  13.7649, 100.5374, 13.7670, 100.5700),
    ("Bangna → Silom",               13.6764, 100.6052, 13.7221, 100.5296),
    ("Silom → Bangna",               13.7221, 100.5296, 13.6764, 100.6052),
    ("On Nut → Sukhumvit Asok",      13.7016, 100.6014, 13.7374, 100.5608),
    ("Bearing → Sukhumvit Asok",     13.6700, 100.6100, 13.7374, 100.5608),
    ("Lad Krabang → Silom",          13.7271, 100.7507, 13.7221, 100.5296),
    ("Minburi → Ratchada",           13.8012, 100.7500, 13.7670, 100.5700),
    ("Pinklao → Silom",              13.7700, 100.4800, 13.7221, 100.5296),
    ("Silom → Pinklao",              13.7221, 100.5296, 13.7700, 100.4800),
    ("Taling Chan → Victory Mon",    13.7811, 100.4600, 13.7649, 100.5374),
    ("Udomsuk → Sukhumvit Asok",     13.6760, 100.6300, 13.7374, 100.5608),
    ("Prawet → Silom",               13.6869, 100.6550, 13.7221, 100.5296),
    ("Lat Phrao → Victory Monument", 13.8122, 100.5701, 13.7649, 100.5374),
    ("Nawamin → Chatuchak",          13.8400, 100.6200, 13.8030, 100.5530),
    ("Kaset Nawamin → Ratchada",     13.8200, 100.6100, 13.7670, 100.5700),
    ("Bang Kapi → Victory Monument", 13.7556, 100.6400, 13.7649, 100.5374),
    ("Thonburi → Silom",             13.7201, 100.4972, 13.7221, 100.5296),
]

# ── Colour palette ────────────────────────────────────────────────────────────
C_PASS = "#27ae60"
C_WARN = "#f39c12"
C_FAIL = "#e74c3c"
C_NONE = "#bdc3c7"
C_SIM  = "#2980b9"
C_GM   = "#e67e22"
C_BG   = "#f4f6f8"

# ── Helpers ───────────────────────────────────────────────────────────────────
_tf = Transformer.from_crs("EPSG:32647", "EPSG:4326", always_xy=True)

def hms_to_sec(t):
    try:
        h, m, s = str(t).split(":")
        return int(h)*3600 + int(m)*60 + int(s)
    except:
        return None

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def next_tuesday():
    today = datetime.date.today()
    days = (1 - today.weekday()) % 7
    return today + datetime.timedelta(days=days if days else 7)

NEXT_TUE = next_tuesday()

def gm_timestamp(hour):
    return datetime.datetime(NEXT_TUE.year, NEXT_TUE.month, NEXT_TUE.day, hour, 0, 0)

# ── Google Maps response cache ────────────────────────────────────────────────
# Shared with travel_time_realism_validator.py — both scripts read/write the
# same file so they always use identical API values and produce the same PASS count.
_CACHE_FILE = os.path.join(os.path.dirname(__file__), "gm_cache.json")
_gm_cache: dict = {}
if os.path.exists(_CACHE_FILE):
    with open(_CACHE_FILE, encoding="utf-8") as _cf:
        _gm_cache = json.load(_cf)

def _cache_key(o_ll, d_ll, hour):
    return f"{o_ll[0]:.6f},{o_ll[1]:.6f}_{d_ll[0]:.6f},{d_ll[1]:.6f}_{hour}_{NEXT_TUE}"

# ── Load trips ────────────────────────────────────────────────────────────────
print("Loading simulation trips …", flush=True)
trips = pd.read_csv(TRIPS_FILE, sep=";", low_memory=False)
trips["trav_sec"]  = trips["trav_time"].apply(hms_to_sec)
trips["trav_min"]  = trips["trav_sec"] / 60
trips["dep_sec"]   = trips["dep_time"].apply(hms_to_sec)
trips["dep_hour"]  = trips["dep_sec"] / 3600
trips["dist_km"]   = trips["traveled_distance"] / 1000

trips = trips[
    (trips["dep_hour"] < 24) &
    (trips["dist_km"] >= MIN_DIST_KM) &
    (trips["dist_km"] <= MAX_DIST_KM) &
    (trips["trav_min"] > 0)
].copy()

print("Converting coordinates …", flush=True)
lons_o, lats_o = _tf.transform(trips["start_x"].values, trips["start_y"].values)
lons_d, lats_d = _tf.transform(trips["end_x"].values,   trips["end_y"].values)
trips["orig_lat"] = lats_o;  trips["orig_lon"] = lons_o
trips["dest_lat"] = lats_d;  trips["dest_lon"] = lons_d
trips = trips[
    ((trips["orig_lat"] - trips["dest_lat"])**2 +
     (trips["orig_lon"] - trips["dest_lon"])**2) > 1e-6
].copy()

print(f"  {len(trips):,} valid trips loaded.", flush=True)

# ── Google Maps client ────────────────────────────────────────────────────────
use_gmaps = GOOGLE_MAPS_API_KEY not in ("YOUR_API_KEY_HERE", "", None)
if use_gmaps:
    try:
        import googlemaps
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        print("  Google Maps API connected.", flush=True)
    except ImportError:
        use_gmaps = False
        print("  googlemaps package not installed — sim-only mode.", flush=True)
else:
    print("  No Google Maps API key — sim-only mode.", flush=True)

def get_gm_time(o_ll, d_ll, hour):
    key = _cache_key(o_ll, d_ll, hour)
    if key in _gm_cache:
        return _gm_cache[key]
    if not use_gmaps:
        return None
    try:
        r = gmaps.distance_matrix(
            origins=[o_ll], destinations=[d_ll],
            mode="driving",
            departure_time=gm_timestamp(hour),
            traffic_model="best_guess",
        )
        el = r["rows"][0]["elements"][0]
        if el["status"] == "OK":
            dur = el.get("duration_in_traffic", el["duration"])
            result = round(dur["value"] / 60, 1)
            _gm_cache[key] = result
            with open(_CACHE_FILE, "w", encoding="utf-8") as _cf:
                json.dump(_gm_cache, _cf, indent=2)
            return result
    except:
        pass
    return None

# ── Compute per-route, per-window results ─────────────────────────────────────
_DEG = SEARCH_RADIUS_KM / 111.0

def agents_near(o_lat, o_lon, d_lat, d_lon):
    om = ((trips["orig_lat"] >= o_lat - _DEG) & (trips["orig_lat"] <= o_lat + _DEG) &
          (trips["orig_lon"] >= o_lon - _DEG) & (trips["orig_lon"] <= o_lon + _DEG))
    dm = ((trips["dest_lat"] >= d_lat - _DEG) & (trips["dest_lat"] <= d_lat + _DEG) &
          (trips["dest_lon"] >= d_lon - _DEG) & (trips["dest_lon"] <= d_lon + _DEG))
    cand = trips[om & dm]
    if len(cand) == 0:
        return cand.index
    R = 6371.0
    def hav(lat1, lon1, lat2c, lon2c):
        dlat = np.radians(lat2c - lat1)
        dlon = np.radians(lon2c - lon1)
        a = np.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
            np.cos(np.radians(lat2c)) * np.sin(dlon/2)**2
        return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    do = hav(o_lat, o_lon, cand["orig_lat"].values, cand["orig_lon"].values)
    dd = hav(d_lat, d_lon, cand["dest_lat"].values, cand["dest_lon"].values)
    return cand[(do <= SEARCH_RADIUS_KM) & (dd <= SEARCH_RADIUS_KM)].index

print("\nComputing route statistics …", flush=True)
rows = []
for rank, (name, o_lat, o_lon, d_lat, d_lon) in enumerate(ROUTES, 1):
    dist_km  = haversine_km(o_lat, o_lon, d_lat, d_lon)
    ridx     = agents_near(o_lat, o_lon, d_lat, d_lon)
    print(f"  [{rank:02d}/{len(ROUTES)}] {name}  ({len(ridx):,} agents)", flush=True)

    for label, hour in QUERY_HOURS.items():
        lo, hi = {7: (7, 9), 12: (11, 13), 17: (17, 19)}[hour]
        sample = trips.loc[
            trips.index.isin(ridx) &
            (trips["dep_hour"] >= lo) & (trips["dep_hour"] < hi),
            "trav_min"
        ].dropna()
        sample = sample[sample <= 120]
        n = len(sample)

        sim_med = round(float(sample.median()), 1) if n >= MIN_AGENTS else None
        gm_time = get_gm_time((o_lat, o_lon), (d_lat, d_lon), hour) if (n >= MIN_AGENTS) else None
        ratio   = round(sim_med / gm_time, 3) if (sim_med and gm_time) else None

        rows.append({
            "rank":    rank,
            "name":    name,
            "window":  label,
            "hour":    hour,
            "dist_km": round(dist_km, 1),
            "n":       n,
            "sim":     sim_med,
            "gm":      gm_time,
            "ratio":   ratio,
        })

df = pd.DataFrame(rows)
df_cmp = df.dropna(subset=["sim", "gm"]).copy()

# ── Derived metrics ───────────────────────────────────────────────────────────
has_cmp = len(df_cmp) > 0

if has_cmp:
    df_cmp["status"] = df_cmp["ratio"].apply(
        lambda r: "PASS" if 0.65 <= r <= 1.35 else ("WARN" if 0.50 <= r <= 1.50 else "FAIL")
    )
    df_cmp["abs_err"] = (df_cmp["sim"] - df_cmp["gm"]).abs()
    df_cmp["err_pct"] = (df_cmp["sim"] - df_cmp["gm"]) / df_cmp["gm"] * 100

    n_pass = (df_cmp["status"] == "PASS").sum()
    n_warn = (df_cmp["status"] == "WARN").sum()
    n_fail = (df_cmp["status"] == "FAIL").sum()
    n_total = len(df_cmp)
    acc_pct = n_pass / n_total * 100

    mape = float(np.mean(np.abs(df_cmp["sim"] - df_cmp["gm"]) / df_cmp["gm"]) * 100)
    mae  = float(np.mean(df_cmp["abs_err"]))
    rmse = float(np.sqrt(np.mean((df_cmp["sim"] - df_cmp["gm"])**2)))
    bias = float(np.mean(df_cmp["sim"] - df_cmp["gm"]))
    bias_pct = bias / float(df_cmp["gm"].mean()) * 100
    med_ratio = float(df_cmp["ratio"].median())
    corr  = float(df_cmp["sim"].corr(df_cmp["gm"]))

    window_acc = {}
    for win in df_cmp["window"].unique():
        sub = df_cmp[df_cmp["window"] == win]
        window_acc[win] = {
            "pass": int((sub["status"] == "PASS").sum()),
            "total": len(sub),
        }

# ── Coverage heatmap data ─────────────────────────────────────────────────────
route_names = [r[0] for r in ROUTES]
win_labels  = list(QUERY_HOURS.keys())

cov_matrix  = np.zeros((len(ROUTES), len(win_labels)))
sim_matrix  = np.full((len(ROUTES), len(win_labels)), np.nan)
ratio_matrix = np.full((len(ROUTES), len(win_labels)), np.nan)
gm_matrix   = np.full((len(ROUTES), len(win_labels)), np.nan)

for _, row in df.iterrows():
    ri = row["rank"] - 1
    wi = win_labels.index(row["window"])
    cov_matrix[ri, wi]  = row["n"]
    if row["sim"] is not None:
        sim_matrix[ri, wi] = row["sim"]
    if row["ratio"] is not None:
        ratio_matrix[ri, wi] = row["ratio"]
    if row["gm"] is not None:
        gm_matrix[ri, wi] = row["gm"]

# ── Build plots ───────────────────────────────────────────────────────────────
print("\nBuilding dashboard …", flush=True)
figs = {}

# ── 1. Scatter: Sim vs Google Maps ────────────────────────────────────────────
if has_cmp:
    fig_scatter = go.Figure()

    # Reference bands (±35%, ±50%)
    max_t = max(df_cmp["gm"].max(), df_cmp["sim"].max()) * 1.15
    xs = np.linspace(0, max_t, 100)
    fig_scatter.add_trace(go.Scatter(
        x=np.concatenate([xs, xs[::-1]]),
        y=np.concatenate([xs * 1.50, xs[::-1] * 0.50]),
        fill="toself", fillcolor="rgba(231,76,60,0.08)",
        line=dict(color="rgba(0,0,0,0)"), name="±50% band", showlegend=True,
        hoverinfo="skip"
    ))
    fig_scatter.add_trace(go.Scatter(
        x=np.concatenate([xs, xs[::-1]]),
        y=np.concatenate([xs * 1.35, xs[::-1] * 0.65]),
        fill="toself", fillcolor="rgba(39,174,96,0.12)",
        line=dict(color="rgba(0,0,0,0)"), name="±35% band (PASS)", showlegend=True,
        hoverinfo="skip"
    ))
    # y = x line
    fig_scatter.add_trace(go.Scatter(
        x=[0, max_t], y=[0, max_t],
        mode="lines", line=dict(color="#555", dash="dot", width=1.5),
        name="Sim = Google Maps", showlegend=True
    ))

    colours = {"PASS": C_PASS, "WARN": C_WARN, "FAIL": C_FAIL}
    for status, grp in df_cmp.groupby("status"):
        fig_scatter.add_trace(go.Scatter(
            x=grp["gm"], y=grp["sim"],
            mode="markers",
            marker=dict(color=colours[status], size=9, opacity=0.85,
                        line=dict(color="white", width=1)),
            name=status,
            customdata=grp[["name", "window", "ratio", "abs_err"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Window: %{customdata[1]}<br>"
                "Sim: %{y:.0f} min   Google: %{x:.0f} min<br>"
                "Ratio: %{customdata[2]:.2f}x   Error: %{customdata[3]:.1f} min"
                "<extra></extra>"
            )
        ))

    fig_scatter.update_layout(
        title=dict(text="Sim vs Google Maps Travel Time", font=dict(size=16)),
        xaxis=dict(title="Google Maps (min)", range=[0, max_t], gridcolor="#e8ecef"),
        yaxis=dict(title="Simulation median (min)", range=[0, max_t], gridcolor="#e8ecef"),
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="v", x=0.01, y=0.99,
                    bgcolor="rgba(255,255,255,0.85)",
                    bordercolor="#ccc", borderwidth=1),
        margin=dict(l=60, r=20, t=50, b=50),
        height=440,
    )
    figs["scatter"] = pio.to_html(fig_scatter, full_html=False, include_plotlyjs=False)

# ── 2. Ratio heatmap ─────────────────────────────────────────────────────────
if has_cmp:
    # Build text annotations
    ratio_text = []
    for ri in range(len(ROUTES)):
        row_text = []
        for wi in range(len(win_labels)):
            v = ratio_matrix[ri, wi]
            row_text.append(f"{v:.2f}x" if not np.isnan(v) else "—")
        ratio_text.append(row_text)

    # Custom colorscale: red(0.5) → yellow(1.0) → green(1.35) → shifted
    # We'll map 0.65–1.35 as green, outside as orange/red
    # Use a diverging scale centred on 1.0
    heatmap_colorscale = [
        [0.0,  "#c0392b"],
        [0.25, "#e74c3c"],
        [0.4,  "#f39c12"],
        [0.5,  "#27ae60"],
        [0.6,  "#f39c12"],
        [0.75, "#e74c3c"],
        [1.0,  "#c0392b"],
    ]

    fig_heatmap = go.Figure(go.Heatmap(
        z=ratio_matrix,
        x=win_labels,
        y=route_names,
        text=ratio_text,
        texttemplate="%{text}",
        textfont=dict(size=10),
        colorscale=heatmap_colorscale,
        zmid=1.0,
        zmin=0.5,
        zmax=1.5,
        colorbar=dict(
            title="Ratio",
            tickvals=[0.5, 0.65, 1.0, 1.35, 1.5],
            ticktext=["0.50 (FAIL)", "0.65", "1.00", "1.35", "1.50 (FAIL)"],
            len=0.8,
        ),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Window: %{x}<br>"
            "Ratio: %{text}<extra></extra>"
        ),
    ))
    fig_heatmap.update_layout(
        title=dict(text="Route Accuracy Heatmap  (Sim / Google Maps ratio)", font=dict(size=16)),
        yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
        xaxis=dict(tickfont=dict(size=12)),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=220, r=20, t=50, b=40),
        height=max(400, 22 * len(ROUTES)),
    )
    figs["heatmap"] = pio.to_html(fig_heatmap, full_html=False, include_plotlyjs=False)

# ── 3. Agent coverage heatmap ─────────────────────────────────────────────────
cov_text = [[str(int(v)) if v > 0 else "0" for v in row] for row in cov_matrix]
fig_cov = go.Figure(go.Heatmap(
    z=cov_matrix,
    x=win_labels,
    y=route_names,
    text=cov_text,
    texttemplate="%{text}",
    textfont=dict(size=10),
    colorscale=[[0, "#ecf0f1"], [0.2, "#aed6f1"], [0.6, "#2980b9"], [1.0, "#1a5276"]],
    colorbar=dict(title="Agents", len=0.8),
    hovertemplate="<b>%{y}</b><br>Window: %{x}<br>Agents: %{text}<extra></extra>",
))
fig_cov.update_layout(
    title=dict(text="Agent Coverage Heatmap  (agents matched per route × window)", font=dict(size=16)),
    yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
    xaxis=dict(tickfont=dict(size=12)),
    plot_bgcolor="white", paper_bgcolor="white",
    margin=dict(l=220, r=20, t=50, b=40),
    height=max(400, 22 * len(ROUTES)),
)
figs["coverage"] = pio.to_html(fig_cov, full_html=False, include_plotlyjs=False)

# ── 4. Travel time bar chart: Sim vs Google Maps per route ────────────────────
if has_cmp:
    # One figure with dropdown for window selection
    all_win = list(QUERY_HOURS.keys())
    fig_bar = go.Figure()

    for wi, win in enumerate(all_win):
        sub = df_cmp[df_cmp["window"] == win].sort_values("sim", ascending=True)
        visible = (wi == 0)
        fig_bar.add_trace(go.Bar(
            name="Simulation", x=sub["name"], y=sub["sim"],
            marker_color=C_SIM, visible=visible,
            error_y=None,
            hovertemplate="<b>%{x}</b><br>Sim: %{y:.0f} min<extra></extra>",
        ))
        fig_bar.add_trace(go.Bar(
            name="Google Maps", x=sub["name"], y=sub["gm"],
            marker_color=C_GM, visible=visible,
            hovertemplate="<b>%{x}</b><br>Google Maps: %{y:.0f} min<extra></extra>",
        ))

    # Dropdown
    n_wins = len(all_win)
    buttons = []
    for wi, win in enumerate(all_win):
        vis = []
        for i in range(n_wins):
            vis += [i == wi, i == wi]   # 2 traces per window
        buttons.append(dict(
            label=win, method="update",
            args=[{"visible": vis}, {"title": f"Simulation vs Google Maps — {win}"}],
        ))

    fig_bar.update_layout(
        title=f"Simulation vs Google Maps — {all_win[0]}",
        barmode="group",
        xaxis=dict(tickangle=-35, tickfont=dict(size=10), gridcolor="#e8ecef"),
        yaxis=dict(title="Travel time (min)", gridcolor="#e8ecef"),
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        updatemenus=[dict(
            buttons=buttons, direction="down",
            showactive=True, x=0.95, y=1.12,
            bgcolor="white", bordercolor="#ccc",
        )],
        margin=dict(l=60, r=20, t=80, b=120),
        height=450,
    )
    figs["bar"] = pio.to_html(fig_bar, full_html=False, include_plotlyjs=False)

# ── 5. Error breakdown bar (routes sorted by MAPE) ───────────────────────────
if has_cmp:
    df_route_err = (
        df_cmp.groupby("name")
        .agg(mape_route=("err_pct", lambda x: np.mean(np.abs(x))),
             mean_ratio=("ratio", "mean"))
        .reset_index()
        .sort_values("mape_route", ascending=False)
    )
    bar_colors = [
        C_PASS if r <= 35 else (C_WARN if r <= 50 else C_FAIL)
        for r in df_route_err["mape_route"]
    ]
    fig_err = go.Figure(go.Bar(
        x=df_route_err["mape_route"],
        y=df_route_err["name"],
        orientation="h",
        marker_color=bar_colors,
        text=[f"{v:.0f}%" for v in df_route_err["mape_route"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>MAPE: %{x:.1f}%<extra></extra>",
    ))
    fig_err.add_vline(x=35, line_dash="dash", line_color=C_PASS,
                      annotation_text="35% PASS", annotation_position="top right")
    fig_err.add_vline(x=50, line_dash="dash", line_color=C_WARN,
                      annotation_text="50% WARN", annotation_position="top right")
    fig_err.update_layout(
        title=dict(text="MAPE per Route  (sorted worst → best)", font=dict(size=16)),
        xaxis=dict(title="MAPE (%)", gridcolor="#e8ecef"),
        yaxis=dict(tickfont=dict(size=11)),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=200, r=80, t=50, b=50),
        height=max(350, 24 * len(df_route_err)),
    )
    figs["err"] = pio.to_html(fig_err, full_html=False, include_plotlyjs=False)

# ── 6. Travel time distribution box plots ─────────────────────────────────────
fig_box = go.Figure()
colours_win = {"AM peak (07:00)": "#2980b9",
               "Midday (12:00)":  "#27ae60",
               "PM peak (17:00)": "#e74c3c"}
for rank, (name, o_lat, o_lon, d_lat, d_lon) in enumerate(ROUTES, 1):
    ridx = df[df["rank"] == rank].index
    for win_label, hour in QUERY_HOURS.items():
        lo, hi = {7: (7, 9), 12: (11, 13), 17: (17, 19)}[hour]
        sample = trips.loc[
            trips.index.isin(
                agents_near(o_lat, o_lon, d_lat, d_lon)
            ) & (trips["dep_hour"] >= lo) & (trips["dep_hour"] < hi),
            "trav_min"
        ].dropna()
        sample = sample[sample <= 120]
        if len(sample) < MIN_AGENTS:
            continue
        fig_box.add_trace(go.Box(
            y=sample.values, name=name,
            boxpoints=False,
            marker_color=colours_win[win_label],
            legendgroup=win_label,
            legendgrouptitle_text=win_label if rank == 1 else "",
            showlegend=(rank == 1),
            hovertemplate=(
                f"<b>{name}</b><br>{win_label}<br>"
                "Median: %{median:.0f} min<extra></extra>"
            ),
        ))

fig_box.update_layout(
    title=dict(text="Simulation Travel Time Distribution by Route", font=dict(size=16)),
    xaxis=dict(tickangle=-40, tickfont=dict(size=9)),
    yaxis=dict(title="Travel time (min)", gridcolor="#e8ecef"),
    plot_bgcolor="white", paper_bgcolor="white",
    boxmode="group",
    legend=dict(orientation="v", x=1.01, y=1),
    margin=dict(l=60, r=160, t=50, b=130),
    height=460,
)
figs["box"] = pio.to_html(fig_box, full_html=False, include_plotlyjs=False)

# ── Build KPI cards HTML ──────────────────────────────────────────────────────
def kpi_card(label, value, sub="", color="#2c3e50", bg="#ffffff"):
    return f"""
    <div style="background:{bg};border-radius:10px;padding:18px 22px;
                box-shadow:0 2px 8px rgba(0,0,0,0.08);min-width:130px;text-align:center;">
      <div style="font-size:11px;color:#7f8c8d;text-transform:uppercase;
                  letter-spacing:0.8px;margin-bottom:6px;">{label}</div>
      <div style="font-size:28px;font-weight:700;color:{color};">{value}</div>
      {f'<div style="font-size:11px;color:#95a5a6;margin-top:4px;">{sub}</div>' if sub else ""}
    </div>"""

if has_cmp:
    acc_color  = C_PASS if acc_pct >= 70 else (C_WARN if acc_pct >= 50 else C_FAIL)
    mape_color = C_PASS if mape <= 25 else (C_WARN if mape <= 40 else C_FAIL)
    bias_color = C_PASS if abs(bias) <= 5 else (C_WARN if abs(bias) <= 10 else C_FAIL)
    bias_sign  = "+" if bias >= 0 else ""
    direction  = "slower" if bias > 0 else "faster"

    kpi_html = f"""
    <div style="display:flex;flex-wrap:wrap;gap:14px;justify-content:flex-start;margin:18px 0;">
      {kpi_card("Accuracy", f"{acc_pct:.0f}%", f"{n_pass}/{n_total} within ±35%", acc_color)}
      {kpi_card("MAPE", f"{mape:.1f}%", "mean abs % error", mape_color)}
      {kpi_card("MAE", f"{mae:.1f} min", "mean abs error", "#2c3e50")}
      {kpi_card("RMSE", f"{rmse:.1f} min", "penalises large errors", "#2c3e50")}
      {kpi_card("Bias", f"{bias_sign}{bias:.1f} min", f"sim is {direction} ({bias_sign}{bias_pct:.0f}%)", bias_color)}
      {kpi_card("Median ratio", f"{med_ratio:.2f}×", "sim / Google Maps", "#2c3e50")}
      {kpi_card("Correlation", f"{corr:.2f}", "Pearson (sim vs GM)", "#2c3e50")}
      {kpi_card("PASS ✅", str(n_pass), f"{n_pass/n_total*100:.0f}%", C_PASS)}
      {kpi_card("WARN ⚠️", str(n_warn), f"{n_warn/n_total*100:.0f}%", C_WARN)}
      {kpi_card("FAIL ❌", str(n_fail), f"{n_fail/n_total*100:.0f}%", C_FAIL)}
    </div>
    <div style="margin-bottom:16px;">
      <span style="font-size:12px;color:#7f8c8d;">
        PASS: ratio 0.65–1.35 &nbsp;|&nbsp; WARN: 0.50–1.50 &nbsp;|&nbsp; FAIL: outside 0.50–1.50
      </span>
    </div>"""

    # Window accuracy mini-table
    win_rows = ""
    for win, acc in window_acc.items():
        pct = acc["pass"] / acc["total"] * 100 if acc["total"] > 0 else 0
        c   = C_PASS if pct >= 60 else (C_WARN if pct >= 40 else C_FAIL)
        win_rows += f"""
        <tr>
          <td style="padding:6px 12px;">{win}</td>
          <td style="padding:6px 12px;text-align:center;font-weight:600;color:{c};">
            {acc['pass']}/{acc['total']} ({pct:.0f}%)
          </td>
        </tr>"""

    kpi_html += f"""
    <div style="background:white;border-radius:10px;padding:16px 20px;
                box-shadow:0 2px 8px rgba(0,0,0,0.08);display:inline-block;
                margin-bottom:20px;">
      <div style="font-size:12px;font-weight:600;color:#2c3e50;margin-bottom:8px;">
        Accuracy by Time Window</div>
      <table style="border-collapse:collapse;font-size:13px;">
        <thead><tr style="background:#f4f6f8;">
          <th style="padding:6px 12px;text-align:left;">Window</th>
          <th style="padding:6px 12px;">PASS rate</th>
        </tr></thead>
        <tbody>{win_rows}</tbody>
      </table>
    </div>"""
else:
    kpi_html = f"""
    <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;
                padding:14px 18px;margin:18px 0;font-size:14px;color:#856404;">
      ⚠️ No Google Maps API key configured — showing simulation data only.<br>
      Set <code>api_keys.google_maps</code> in <code>config.json</code> to enable full validation.
    </div>"""

# ── Window accuracy bar chart ─────────────────────────────────────────────────
if has_cmp:
    win_names = list(window_acc.keys())
    win_pass_pct = [window_acc[w]["pass"] / window_acc[w]["total"] * 100
                    for w in win_names]
    win_colors   = [C_PASS if p >= 60 else (C_WARN if p >= 40 else C_FAIL)
                    for p in win_pass_pct]

    fig_win = go.Figure(go.Bar(
        x=win_pass_pct, y=win_names, orientation="h",
        marker_color=win_colors,
        text=[f"{p:.0f}%" for p in win_pass_pct],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>PASS rate: %{x:.0f}%<extra></extra>",
    ))
    fig_win.add_vline(x=60, line_dash="dash", line_color="#555",
                      annotation_text="60% target", annotation_position="top right")
    fig_win.update_layout(
        title=dict(text="PASS Rate by Time Window", font=dict(size=16)),
        xaxis=dict(title="PASS rate (%)", range=[0, 110], gridcolor="#e8ecef"),
        yaxis=dict(tickfont=dict(size=13)),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=160, r=60, t=50, b=40),
        height=220,
    )
    figs["win_acc"] = pio.to_html(fig_win, full_html=False, include_plotlyjs=False)

# ── Assemble HTML ─────────────────────────────────────────────────────────────
plotlyjs_cdn = '<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>'

def section(title, content, collapsible=False):
    if collapsible:
        uid = title.lower().replace(" ", "_").replace("(", "").replace(")", "")
        return f"""
        <details open style="margin-bottom:28px;">
          <summary style="cursor:pointer;font-size:17px;font-weight:600;
                          color:#2c3e50;padding:10px 0;border-bottom:2px solid #e0e6ed;
                          margin-bottom:16px;">{title}</summary>
          {content}
        </details>"""
    return f"""
    <div style="margin-bottom:32px;">
      <h2 style="font-size:17px;font-weight:600;color:#2c3e50;
                 border-bottom:2px solid #e0e6ed;padding-bottom:8px;
                 margin-bottom:16px;">{title}</h2>
      {content}
    </div>"""

def two_col(left, right, left_w="50%", right_w="50%"):
    # Use explicit flex-basis so the widths are actually respected
    gap = 18
    return f"""
    <div style="display:flex;gap:{gap}px;flex-wrap:wrap;margin-bottom:28px;">
      <div style="flex:0 0 calc({left_w} - {gap//2}px);min-width:320px;overflow:hidden;">{left}</div>
      <div style="flex:0 0 calc({right_w} - {gap//2}px);min-width:320px;overflow:hidden;">{right}</div>
    </div>"""

# Build body
body_parts = []

# ── Summary KPIs
body_parts.append(section("Validation Summary", kpi_html))

# ── Scatter + window accuracy (stacked: scatter full-width, bar below)
if has_cmp:
    scatter_block = figs.get("scatter", "")
    win_acc_block = figs.get("win_acc", "")
    body_parts.append(section(
        "Travel Time Comparison",
        f'<div style="margin-bottom:12px;">{scatter_block}</div>'
        f'<div>{win_acc_block}</div>'
    ))

# ── Sim vs Google Maps bar chart
if has_cmp:
    body_parts.append(section(
        "Per-Route Travel Time  (use dropdown to switch window)",
        figs.get("bar", ""), collapsible=True
    ))

# ── Ratio heatmap
if has_cmp:
    body_parts.append(section(
        "Route Accuracy Heatmap  (ratio = Sim ÷ Google Maps)",
        figs.get("heatmap", ""), collapsible=True
    ))

# ── MAPE error bar
if has_cmp:
    body_parts.append(section(
        "Error Breakdown by Route  (MAPE)",
        figs.get("err", ""), collapsible=True
    ))

# ── Coverage heatmap
body_parts.append(section(
    "Agent Coverage  (agents matched per route × window)",
    figs.get("coverage", ""), collapsible=True
))

# ── Box plots
body_parts.append(section(
    "Simulation Travel Time Distribution by Route",
    figs.get("box", ""), collapsible=True
))

api_badge = (
    '<span style="background:#27ae60;color:white;padding:3px 9px;border-radius:4px;'
    'font-size:12px;">Google Maps API connected</span>'
    if use_gmaps else
    '<span style="background:#e67e22;color:white;padding:3px 9px;border-radius:4px;'
    'font-size:12px;">Simulation only — no API key</span>'
)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bangkok MATSim Validation Dashboard</title>
  {plotlyjs_cdn}
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: {C_BG}; color: #2c3e50; margin: 0; padding: 0;
    }}
    .header {{
      background: linear-gradient(135deg, #1a252f 0%, #2c3e50 100%);
      color: white; padding: 28px 40px;
    }}
    .header h1 {{ margin: 0 0 6px; font-size: 24px; font-weight: 700; }}
    .header p  {{ margin: 0; font-size: 13px; color: #bdc3c7; }}
    .main {{ max-width: 1400px; margin: 0 auto; padding: 30px 40px; }}
    details > summary::-webkit-details-marker {{ color: #3498db; }}
    details > summary::marker {{ color: #3498db; }}
    @media (max-width: 768px) {{
      .main {{ padding: 16px; }}
      .header {{ padding: 20px; }}
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Bangkok MATSim Validation Dashboard</h1>
    <p>
      Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")} &nbsp;|&nbsp;
      Reference date: {NEXT_TUE} (Tuesday) &nbsp;|&nbsp;
      Routes: {len(ROUTES)} &nbsp;|&nbsp;
      Search radius: {SEARCH_RADIUS_KM} km &nbsp;|&nbsp;
      {api_badge}
    </p>
  </div>
  <div class="main">
    {"".join(body_parts)}
  </div>
</body>
</html>"""

# ── Save ──────────────────────────────────────────────────────────────────────
with open(OUT_HTML, "w", encoding="utf-8") as _f:
    _f.write(html)

print(f"\n✅  Dashboard saved: {OUT_HTML}")
print(f"    Open in any browser to view.")
