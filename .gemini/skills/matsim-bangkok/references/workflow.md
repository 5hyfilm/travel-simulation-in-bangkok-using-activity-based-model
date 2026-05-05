# MATSim Bangkok Simulation Workflow

This guide covers the end-to-end process of preparing and running the Bangkok travel simulation.

## 1. Data Preprocessing (Python)
Extracts OSM data and generates activity-based population plans.
- **Command**: `cd pipeline && python3 main.py`
- **Output**: `data/pathumwan_M.osm`, `pipeline/data/final_trips.csv`, etc.
- **Troubleshooting**: Ensure `customtkinter` and `pywebview` are installed for GUI tools.

## 2. Network Preparation (Java)
Converts raw OSM data into MATSim network format and cleans it.
- **Conversion**: `./mvnw exec:java -Dexec.mainClass="org.matsim.project.ConvertOSM"`
- **Cleaning**: `./mvnw exec:java -Dexec.mainClass="org.matsim.project.RunNetworkCleaner"`
- **Why**: The cleaner is essential to ensure all links are reachable and to fix disconnected sub-networks that cause simulation crashes.

## 3. Simulation Execution (Java)
Runs the mobsim with specific configurations.
- **Standard Run**: `./mvnw exec:java -Dexec.mainClass="org.matsim.project.RunMatsim"`
- **Adaptive Signals (Lämmer)**: `./mvnw exec:java -Dexec.mainClass="org.matsim.project.RunLaemmerSimulation"`
- **Memory Management**: If OOM occurs, use `MAVEN_OPTS="-Xmx16G"` or adjust the `config.json` file.

## 4. Evaluation and Analysis
Post-simulation scripts for validation.
- **Scripts location**: `evaluation/` and `pipeline/analysis/`
- **Visualization**: Use SimWrapper on the `output/` directory. Coordinate system is `EPSG:32647`.
