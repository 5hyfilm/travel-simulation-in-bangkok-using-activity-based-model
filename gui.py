"""
config_gui.py
=============
Modern GUI for editing config.json before running the MATSim Bangkok pipeline.

Run from project root:
    python config_gui.py

Requirements:
    pip install customtkinter pywebview
"""

import json
import os
import platform
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

try:
    import webview
    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH  = os.path.join(PROJECT_ROOT, "config.json")
BANGKOK_LAT = 13.75
BANGKOK_LON = 100.52

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ── Config I/O ─────────────────────────────────────────────────────────────────

def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


# ── Reusable widgets ───────────────────────────────────────────────────────────

def section_title(parent, text):
    ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=12, weight="bold"),
                 text_color=("#1a73e8", "#5ea4ff")).pack(anchor="w", padx=4, pady=(14, 2))
    ctk.CTkFrame(parent, height=1, fg_color=("#d0d0d0", "#3a3a3a")).pack(fill="x", padx=4, pady=(0, 6))

def labeled_entry(parent, label, value="", width=200):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=4, pady=3)
    ctk.CTkLabel(frame, text=label, width=180, anchor="e",
                 font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
    var = ctk.StringVar(value=str(value))
    ctk.CTkEntry(frame, textvariable=var, width=width).pack(side="left")
    return var

def _smart_path(path):
    """Return a relative path if inside the project, otherwise absolute.

    os.path.relpath raises ValueError on Windows when path and PROJECT_ROOT
    are on different drives, so we always fall back to the absolute path.
    """
    try:
        rel = os.path.relpath(path, PROJECT_ROOT)
        # Paths that start with '..' are outside the project root — use absolute
        if rel.startswith(".."):
            return os.path.abspath(path)
        return rel
    except ValueError:
        # Different drive on Windows
        return os.path.abspath(path)

def labeled_file(parent, label, value="", filetypes=None, width=260):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=4, pady=3)
    ctk.CTkLabel(frame, text=label, width=180, anchor="e",
                 font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
    var = ctk.StringVar(value=str(value))
    ent = ctk.CTkEntry(frame, textvariable=var, width=width)
    ent.pack(side="left", padx=(0, 6))
    def browse():
        path = filedialog.askopenfilename(filetypes=filetypes or [("All files", "*.*")])
        if path:
            var.set(_smart_path(path))
    ctk.CTkButton(frame, text="Browse", width=70, command=browse).pack(side="left")
    return var

def labeled_dir(parent, label, value="", width=260):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=4, pady=3)
    ctk.CTkLabel(frame, text=label, width=180, anchor="e",
                 font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
    var = ctk.StringVar(value=str(value))
    ent = ctk.CTkEntry(frame, textvariable=var, width=width)
    ent.pack(side="left", padx=(0, 6))
    def browse():
        path = filedialog.askdirectory()
        if path:
            var.set(_smart_path(path))
    ctk.CTkButton(frame, text="Browse", width=70, command=browse).pack(side="left")
    return var

def labeled_switch(parent, label, value=False):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=4, pady=3)
    ctk.CTkLabel(frame, text=label, width=180, anchor="e",
                 font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
    var = ctk.BooleanVar(value=bool(value))
    ctk.CTkSwitch(frame, variable=var, text="").pack(side="left")
    return var


# ── Map picker (pywebview + Leaflet.js) ────────────────────────────────────────

MAP_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>Pick Bounding Box</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css"/>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1e1e1e; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; height: 100vh; }
  #map { flex: 1; }
  #bar {
    background: #2b2b2b;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-top: 1px solid #3a3a3a;
  }
  #coords {
    flex: 1;
    color: #aaa;
    font-size: 13px;
  }
  #coords span { color: #5ea4ff; font-weight: bold; margin-left: 4px; }
  button {
    padding: 8px 22px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
  }
  #btn-confirm { background: #1a73e8; color: white; }
  #btn-confirm:hover { background: #1558b0; }
  #btn-confirm:disabled { background: #444; color: #777; cursor: default; }
  #btn-reset  { background: #444; color: #ccc; }
  #btn-reset:hover { background: #555; }
</style>
</head>
<body>
<div id="map"></div>
<div id="bar">
  <div id="coords">
    Draw a rectangle on the map &nbsp;|&nbsp;
    N:<span id="cn">—</span>
    S:<span id="cs">—</span>
    E:<span id="ce">—</span>
    W:<span id="cw">—</span>
  </div>
  <button id="btn-reset"   onclick="resetBox()">Reset</button>
  <button id="btn-confirm" onclick="confirm()" disabled>Confirm</button>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"></script>
<script>
  var map = L.map('map').setView([INIT_LAT, INIT_LON], 11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors', maxZoom: 19
  }).addTo(map);

  var drawnItems = new L.FeatureGroup();
  map.addLayer(drawnItems);

  var drawControl = new L.Control.Draw({
    draw: {
      rectangle: { shapeOptions: { color: '#1a73e8', fillOpacity: 0.08, weight: 2 } },
      polyline: false, polygon: false, circle: false,
      marker: false, circlemarker: false
    },
    edit: { featureGroup: drawnItems }
  });
  map.addControl(drawControl);

  var currentBbox = null;

  // Show existing bbox if provided
  var initBbox = INIT_BBOX;
  if (initBbox) {
    var rect = L.rectangle([[initBbox.s, initBbox.w],[initBbox.n, initBbox.e]],
                           {color:'#1a73e8', fillOpacity:0.08, weight:2});
    drawnItems.addLayer(rect);
    updateCoords(initBbox.n, initBbox.s, initBbox.e, initBbox.w);
  }

  map.on(L.Draw.Event.CREATED, function(e) {
    drawnItems.clearLayers();
    drawnItems.addLayer(e.layer);
    var b = e.layer.getBounds();
    updateCoords(b.getNorth(), b.getSouth(), b.getEast(), b.getWest());
  });

  map.on(L.Draw.Event.EDITED, function(e) {
    e.layers.eachLayer(function(layer) {
      var b = layer.getBounds();
      updateCoords(b.getNorth(), b.getSouth(), b.getEast(), b.getWest());
    });
  });

  // REAL-TIME UPDATES: Listen for move and resize during the drag action
  map.on('draw:editmove draw:editresize', function(e) {
    var layer = e.layer;
    var b = layer.getBounds();
    updateCoords(b.getNorth(), b.getSouth(), b.getEast(), b.getWest());
  });

  map.on(L.Draw.Event.DELETED, function() {
    currentBbox = null;
    document.getElementById('cn').textContent = '—';
    document.getElementById('cs').textContent = '—';
    document.getElementById('ce').textContent = '—';
    document.getElementById('cw').textContent = '—';
    document.getElementById('btn-confirm').disabled = true;
  });

  function updateCoords(n, s, e, w) {
    currentBbox = { n: n, s: s, e: e, w: w };
    document.getElementById('cn').textContent = n.toFixed(5);
    document.getElementById('cs').textContent = s.toFixed(5);
    document.getElementById('ce').textContent = e.toFixed(5);
    document.getElementById('cw').textContent = w.toFixed(5);
    document.getElementById('btn-confirm').disabled = false;
  }

  function resetBox() {
    drawnItems.clearLayers();
    currentBbox = null;
    document.getElementById('cn').textContent = '—';
    document.getElementById('cs').textContent = '—';
    document.getElementById('ce').textContent = '—';
    document.getElementById('cw').textContent = '—';
    document.getElementById('btn-confirm').disabled = true;
  }

  function confirm() {
    if (!currentBbox) return;
    window.pywebview.api.confirm_bbox(
      currentBbox.n, currentBbox.s, currentBbox.e, currentBbox.w
    );
  }
</script>
</body>
</html>
"""

import multiprocessing

def _map_process_wrapper(queue, init_n, init_s, init_e, init_w):
    """Worker function that runs in a separate process to avoid GUI conflicts."""
    try:
        import webview
        
        result = {"n": 0, "s": 0, "e": 0, "w": 0, "confirmed": False}

        class BboxAPI:
            def confirm_bbox(self, n, s, e, w):
                result.update({"n": n, "s": s, "e": e, "w": w, "confirmed": True})
                win.destroy()

        bbox_js = f"{{n:{init_n},s:{init_s},e:{init_e},w:{init_w}}}" if init_n is not None else "null"
        html = (MAP_HTML
                .replace("INIT_LAT", str(BANGKOK_LAT))
                .replace("INIT_LON", str(BANGKOK_LON))
                .replace("INIT_BBOX", bbox_js))

        api = BboxAPI()
        win = webview.create_window("Pick Bounding Box — Bangkok MATSim", html=html, js_api=api, width=900, height=680)
        webview.start()
        
        if result["confirmed"]:
            queue.put(result)
    except Exception as e:
        print(f"Map Process Error: {e}")

def open_map_picker(v_north, v_south, v_east, v_west, parent_root):
    """Open the map picker in a separate process to avoid GIL/Cocoa crashes on macOS."""
    
    try:
        init_n, init_s = float(v_north.get()), float(v_south.get())
        init_e, init_w = float(v_east.get()), float(v_west.get())
    except:
        init_n = init_s = init_e = init_w = None

    # Use a Queue to get the result back from the process
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(
        target=_map_process_wrapper, 
        args=(queue, init_n, init_s, init_e, init_w)
    )
    
    # Disable parent while map is open
    if platform.system() == "Windows":
        parent_root.attributes("-disabled", True)
    
    p.start()
    
    # Poll the queue or wait for process
    def check_process():
        if not p.is_alive():
            if not queue.empty():
                res = queue.get()
                v_north.set(str(round(res["n"], 6)))
                v_south.set(str(round(res["s"], 6)))
                v_east.set(str(round(res["e"], 6)))
                v_west.set(str(round(res["w"], 6)))
            
            if platform.system() == "Windows":
                parent_root.attributes("-disabled", False)
            parent_root.lift()
            parent_root.focus_force()
        else:
            parent_root.after(200, check_process)

    parent_root.after(200, check_process)


# ── Main GUI ───────────────────────────────────────────────────────────────────

def build_gui(config):
    root = ctk.CTk()
    root.title("A2M Pipeline — Configuration & Simulation Run")
    root.geometry("640x580")
    root.resizable(False, False)

    # Header
    header = ctk.CTkFrame(root, fg_color=("#1a73e8", "#1558b0"), corner_radius=0)
    header.pack(fill="x")
    ctk.CTkLabel(header, text="A2M Pipeline",
                 font=ctk.CTkFont(size=18, weight="bold"),
                 text_color="white").pack(side="left", padx=16, pady=10)
    ctk.CTkLabel(header, text="Configuration Editor",
                 font=ctk.CTkFont(size=12),
                 text_color="#cce0ff").pack(side="left", pady=10)

    # Tabview
    tabs = ctk.CTkTabview(root, anchor="nw")
    tabs.pack(fill="both", expand=True, padx=12, pady=(8, 4))
    for name in ["Input", "Execution", "API Keys"]:
        tabs.add(name)

    # ── Input tab ─────────────────────────────────────────────────
    t = tabs.tab("Input")
    inp = config["input"]

    section_title(t, "Bounding Box")
    v_north = labeled_entry(t, "North", inp["north"])
    v_south = labeled_entry(t, "South", inp["south"])
    v_east  = labeled_entry(t, "East",  inp["east"])
    v_west  = labeled_entry(t, "West",  inp["west"])

    map_row = ctk.CTkFrame(t, fg_color="transparent")
    map_row.pack(fill="x", padx=4, pady=(4, 2))
    ctk.CTkLabel(map_row, text="", width=188).pack(side="left")
    if MAP_AVAILABLE:
        ctk.CTkButton(
            map_row, text="🗺  Pick on Map…", width=160,
            command=lambda: open_map_picker(v_north, v_south, v_east, v_west, root)
        ).pack(side="left")
    else:
        ctk.CTkLabel(map_row, text="pip install pywebview  to enable map picker",
                     font=ctk.CTkFont(size=11), text_color="gray").pack(side="left")

    section_title(t, "Input Files")
    v_trips  = labeled_file(t, "ActivitySim Trips (.csv)",    inp["trips_filename"],
                            [("CSV", "*.csv"), ("All", "*.*")])
    v_subdis = labeled_file(t, "Subdistricts Shapefile (.geojson)", inp["subdistricts_filename"],
                            [("GeoJSON", "*.geojson"), ("All", "*.*")])

    section_title(t, "Simulation")
    v_sample = labeled_entry(t, "Sample Size", inp["sample_size"])

    # ── Execution tab ─────────────────────────────────────────────
    t = tabs.tab("Execution")
    exc = config.get("execution", {})

    section_title(t, "MATSim")
    v_auto    = labeled_switch(t, "Run Full Pipeline",
                               exc.get("run_simulation_automatically", False))
    v_mvnopts = labeled_entry(t, "Maven Opts (Memory Option)", exc.get("maven_opts", "-Xmx10G"))
    v_mscfg   = labeled_file(t, "MATSim Config File", exc.get("matsim_config_file", ""),
                              [("XML", "*.xml"), ("All", "*.*")])

    section_title(t, "Traffic Conditions")
    v_tc     = labeled_switch(t, "Apply Traffic Conditions",
                               exc.get("apply_traffic_conditions", False))
    v_tcfile = labeled_file(t, "Conditions File",
                            exc.get("traffic_conditions_file", "data/traffic_conditions.json"),
                            [("JSON", "*.json"), ("All", "*.*")])

    # ── API Keys tab ──────────────────────────────────────────────
    t = tabs.tab("API Keys")
    api = config.get("api_keys", {})
    section_title(t, "Google Maps")
    v_gmaps = labeled_entry(t, "API Key", api.get("google_maps", ""), width=320)

    # ── Bottom bar ────────────────────────────────────────────────
    bar = ctk.CTkFrame(root, fg_color="transparent")
    bar.pack(fill="x", padx=12, pady=(0, 10))

    def on_save(run_after=False):
        try:
            new_cfg = {
                "input": {
                    "north":                 float(v_north.get()),
                    "south":                 float(v_south.get()),
                    "east":                  float(v_east.get()),
                    "west":                  float(v_west.get()),
                    "trips_filename":        v_trips.get().strip(),
                    "subdistricts_filename": v_subdis.get().strip(),
                    "sample_size":           int(v_sample.get()),
                },
                "execution": {
                    "run_simulation_automatically": v_auto.get(),
                    "maven_opts":                   v_mvnopts.get().strip(),
                    "matsim_config_file":           v_mscfg.get().strip(),
                    "apply_traffic_conditions":     v_tc.get(),
                    "traffic_conditions_file":      v_tcfile.get().strip(),
                },
                "api_keys": {
                    "google_maps": v_gmaps.get().strip(),
                },
            }
            save_config(new_cfg)
            if not run_after:
                messagebox.showinfo("Saved", f"Configuration saved to:\n{CONFIG_PATH}")
            return True
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            return False

    def on_run():
        project_root = os.path.dirname(os.path.abspath(__file__))
        system = platform.system()
        
        try:
            if system == "Windows":
                script_path = os.path.join(project_root, "run.bat")
                # Start a new CMD window and keep it open (/k) if it fails, or just run it
                subprocess.Popen(["start", "cmd", "/c", script_path], shell=True)
            elif system == "Darwin": # macOS
                script_path = os.path.join(project_root, "run.sh")
                # Use osascript to open a new Terminal window for visibility
                cmd = f'tell application "Terminal" to do script "cd \'{project_root}\' && chmod +x run.sh && ./run.sh"'
                subprocess.Popen(["osascript", "-e", cmd])
            else: # Linux
                script_path = os.path.join(project_root, "run.sh")
                # Try to find a terminal emulator
                terminals = ["gnome-terminal", "xterm", "konsole"]
                success = False
                for term in terminals:
                    if subprocess.run(["which", term], capture_output=True).returncode == 0:
                        subprocess.Popen([term, "-e", f"bash -c 'cd {project_root} && chmod +x run.sh && ./run.sh; exec bash'"])
                        success = True
                        break
                if not success:
                    subprocess.Popen(["bash", script_path], cwd=project_root)
        except Exception as e:
            messagebox.showerror("Run Error", f"Could not start the simulation:\n{str(e)}")

    def on_save_and_run():
        if on_save(run_after=True):
            on_run()

    ctk.CTkButton(bar, text="Save & Run 🚀", width=140, fg_color="#28a745", 
                  hover_color="#218838", command=on_save_and_run).pack(side="right", padx=4)
    ctk.CTkButton(bar, text="Apply Config",   width=90, command=lambda: on_save()).pack(side="right", padx=4)
    ctk.CTkButton(bar, text="Cancel", width=90, fg_color="#555",
                  hover_color="#666", command=root.destroy).pack(side="right", padx=4)

    root.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    cfg = load_config()
    build_gui(cfg)
