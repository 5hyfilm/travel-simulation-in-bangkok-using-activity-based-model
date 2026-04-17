# Installation & Setup

## 1. Prerequisites

- Python 3.9 or higher
- Internet connection (for Overpass API)

## 2. Set up Virtual Environment

Open your terminal or command prompt and run the following commands:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

## 3. Install Dependencies

Install the required Python libraries:

```bash
pip install -r requirements.txt
```

---

# How to Run

1. **Prepare Inputs**: 
   - Place your **`trips.csv`** file in the `preprocess/` directory (This is required for Step 4 & 5).
   - The script will automatically detect and process it.

2. **Configure (Optional)**: Open `config.json` in the root directory to adjust coordinates or sample size. The current default is a wide area of Greater Bangkok:
   ```json
   {
       "input": {
           "north": 13.96,
           "south": 13.49,
           "east": 100.96,
           "west": 100.33,
           "trips_filename": "data/final_trips.csv",
           "subdistricts_filename": "data/subdistricts_180.geojson",
           "sample_size": 500000
       },
       "execution": {
           "run_simulation_automatically": true
       }
   }
   ```

   > [!TIP]
   > Setting `"sample_size": -1` or `None` will skip sampling and include **all unique persons** from the `trips.csv` file in the generated MATSim plans.

3. Run the pipeline:

   **Option A: One-Click Runner (Recommended)**
   Run the full pipeline (Environment Activation -> Preprocess -> MATSim Java Simulation) from the project root:
   ```bash
   ./run.sh
   ```

   **Option B: Manual Python Execution**
   ```bash
   cd preprocess
   python main.py
   ```

4. The script will execute the following steps automatically:
   - **[Step 1-5]:** Preprocessing (Download OSM, Extract POIs, Clean, Assign Locations, Generate `plan_all.xml`).
   - **[Step 6-8]:** MATSim Execution (Convert OSM, Clean Network, Run Simulation) - *if enabled in config.json*.

---

# Export Signal Locations

Signal location export is a separate post-processing step. It is **not** part of `python main.py`, because it depends on Java-generated network and signal files.

Run the full flow in this order:

1. Run the Python preprocess pipeline:

   ```bash
   python main.py
   ```

2. Run the Java network and signal generation steps:

   ```bash
   # run these Java classes using your usual MATSim/IDE workflow
   org.matsim.project.ConvertOSM
   org.matsim.project.RunNetworkCleaner
   ```

3. Export signal locations for QGIS or inspection:

   ```bash
   python export_signal_locations.py
   ```

`signal_locations.csv` and `signal_locations.geojson` are optional post-processing outputs generated only after the Java steps are complete.

---

# Output Files

All results are saved in the `output/` folder:

| File Name                   | Description                                                                                                    |
| :-------------------------- | :------------------------------------------------------------------------------------------------------------- |
| **`network.osm`**           | Raw OpenStreetMap XML data (Highways, Buildings, Landuse).                                                     |
| **`facilities_raw.csv`**    | Raw POI data extracted directly from OSM.                                                                      |
| **`facilities_cleaned.csv`**| Filtered and classified POIs with MATSim activity types.                                                       |
| **`final_trips.csv`**       | Intermediate file: Trips mapping actual facilities for each activity.                                          |
| **`plan_20k.xml`**          | **Final MATSim Plan**. Ready to be used for simulation! (XML v6).                                              |
| **`signal_locations.csv`**  | Optional post-processing output: signal junction coordinates (node_id, UTM x/y, lat/lon, num_signals). Generated only after the Java signal steps are run and `export_signal_locations.py` is executed. |
| **`signal_locations.geojson`** | Optional post-processing output: GeoJSON PointFeatureCollection of signal junctions. Open in QGIS: drag the file into the Layers panel, then add OpenStreetMap basemap via XYZ Tiles for context. |
