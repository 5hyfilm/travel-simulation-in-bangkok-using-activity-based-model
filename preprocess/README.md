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

2. **Configure (Optional)**: Open `main.py` to adjust coordinates or sample size. The current default is a wide area of Bangkok:
   ```python
   config = {
       "north": 13.78264,
       "south": 13.71056,
       "east":  100.57110,
       "west":  100.49690,
       "output_folder": "output",
       "osm_filename": "network.osm",
       "raw_csv_filename": "facilities_raw.csv",       
       "clean_csv_filename": "facilities_cleaned.csv",
       "trips_filename": "trips.csv", # Input from behavior layer (User should provide this)
       "final_trips_filename": "final_trips.csv",
       "plans_filename": "plan_20k.xml",
       "sample_size": 20000 # Use -1 or None to select ALL persons
   }
   ```

   > [!TIP]
   > Setting `"sample_size": -1` or `None` will skip sampling and include **all unique persons** from the `trips.csv` file in the generated MATSim plans.

2. Run the main script:

   ```bash
   python main.py
   ```

3. The script will execute the following **6 steps** automatically:
   - **[Step 1/6]:** Download `.osm` network file (Swiss Mirror).
   - **[Step 2/6]:** Extract raw facilities/POIs to CSV.
   - **[Step 3/6]:** Clean names, classify activities (Home/Work/Study/Shop etc.).
   - **[Step 4/6]:** **Location Assignment**: Maps `trips.csv` to specific coordinates.
   - **[Step 5/6]:** **Plan Generation**: Creates `plan_20k.xml` ready for MATSim.
   - **[Step 6/6]:** **Signal Export**: Exports signal junction coordinates to CSV and GeoJSON (skipped if Java signal files are not yet generated).

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
| **`signal_locations.csv`**  | Signal junction coordinates (node_id, UTM x/y, lat/lon, num_signals). Generated after Java steps are run.     |
| **`signal_locations.geojson`** | GeoJSON PointFeatureCollection of signal junctions. Drag into QGIS or kepler.gl to visualize on a map.     |

