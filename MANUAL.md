# 🚗 Bangkok MATSim Simulation Manual (Adaptive Signals)

This guide provides a complete walk-through for preparing and running the **Bangkok Activity-Based Model** simulation using **Lämmer's adaptive traffic signal control**.

---

## 🛠️ Phase 1: Data Preprocessing (Python)
This step prepares the road network, activity locations (POIs), and populates 20,000 car agents into a MATSim plan file.

1.  **Navigate to the pipeline folder**:
    ```bash
    cd pipeline
    ```
2.  **Ensure you have `trips.csv`** in the `pipeline/` folder.
3.  **Run the automated pipeline**:
    ```bash
    python3 main.py
    ```
    - **Step 1/6**: Downloads Bangkok OSM map (Swiss Mirror).
    - **Step 2/6**: Extracts POIs from OSM.
    - **Step 3/6**: Classifies POIs for MATSim activities.
    - **Step 4/6**: Assigns actual coordinates to trip data.
    - **Step 5/6**: Generates `plan_20k.xml`.
    - **Step 6/6**: Exports signal junction locations to `output/signal_locations.csv` and `output/signal_locations.geojson` (skipped if Java signal files are not yet generated — run Phase 2 first, then re-run `main.py`).

---

## ⚙️ Phase 2: Network Conversion & Cleaning (Java)
Converts the OSM file into a MATSim network and ensures connectivity.

Run these from the **Project Root**:

### 1. Convert OSM to MATSim XML
Generates the network and signals for junctions.
```bash
./mvnw exec:java -Dexec.mainClass="org.matsim.project.ConvertOSM"
```

### 2. Clean the Network
Removes disconnected road islands to prevent simulation crashes.
```bash
./mvnw exec:java -Dexec.mainClass="org.matsim.project.RunNetworkCleaner"
```

---

## 🚀 Phase 3: Run the Simulation (Java)

### Option A: Without signals (standard MATSim)
Use `RunMatsim` if you want to run a basic simulation without any traffic signal control. Note that this requires a `config.xml` file pointing to your network and plans.
```bash
./mvnw exec:java -Dexec.mainClass="org.matsim.project.RunMatsim"
```

### Option B: With Lämmer Adaptive Signal Control
```bash
./mvnw exec:java -Dexec.mainClass="org.matsim.project.RunLaemmerSimulation"
```

### ⚡ Tuning Parameters
You can adjust the following in `RunLaemmerSimulation.java`:
- **Iterations**: `config.controller().setLastIteration(0);` (Default is 0 for fast results).
- **Signal Frequency**: `ThrottledSignalEngine.setUpdateInterval(5);` (Default is 5s for performance).

---

## 📊 Analyzing Results
Outputs are located in `output/laemmer_simulation/`.
- **Events**: `output_events.xml.gz` (Detailed movement logs).
- **Analysis**: Check the `analysis/` folder for CSV stats (stuck agents, mode share).
- **Visualization**: Drag the entire output folder into [SimWrapper](https://vsp.berlin/simwrapper/).
    - > [!IMPORTANT]
    - > When using **SimWrapper**, ensure you set the coordinate system to **`EPSG:32647`** (WGS 84 / UTM zone 47N) to correctly align the simulation results with the map of Bangkok.

## 🗺️ Visualizing Signal Locations
After running Phase 2 and re-running `main.py`, signal junction locations are exported to `pipeline/output/`:
- **`signal_locations.csv`** — node ID, UTM coordinates, lat/lon, and number of signals per junction.
- **`signal_locations.geojson`** — open in QGIS by dragging the file into the Layers panel, then add an OpenStreetMap basemap via XYZ Tiles for context.

---
**Branch**: `film-laemmer`
