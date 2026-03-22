# 🚗 Bangkok MATSim Simulation Manual (Adaptive Signals)

This guide provides a complete walk-through for preparing and running the **Bangkok Activity-Based Model** simulation using **Lämmer's adaptive traffic signal control**.

---

## 🛠️ Phase 1: Data Preprocessing (Python)
This step prepares the road network, activity locations (POIs), and populates 20,000 car agents into a MATSim plan file.

1.  **Navigate to the preprocess folder**:
    ```bash
    cd preprocess
    ```
2.  **Ensure you have `trips.csv`** in the `preprocess/` folder.
3.  **Run the automated pipeline**:
    ```bash
    python3 main.py
    ```
    - **Step 1/5**: Downloads Bangkok OSM map (Swiss Mirror).
    - **Step 2/5**: Extracts POIs from OSM.
    - **Step 3/5**: Classifies POIs for MATSim activities.
    - **Step 4/5**: Assigns actual coordinates to trip data.
    - **Step 5/5**: Generates `plan_20k.xml`.

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
Executes the final simulation with **Adaptive Signal Control**.

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

---
**Branch**: `film-laemmer`
