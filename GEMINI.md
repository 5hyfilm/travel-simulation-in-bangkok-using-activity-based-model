# Gemini Project Context: Travel Simulation in Bangkok (MATSim)

This project implements a multi-agent transport simulation (MATSim) for Bangkok, utilizing an Activity-Based Model and adaptive traffic signal control (Lämmer's algorithm).

## 🏗️ Project Overview
- **Purpose**: Simulate urban travel patterns in Bangkok (primarily Pathum Wan district) to evaluate traffic conditions and signal control strategies.
- **Main Technologies**:
    - **Java (21+)**: Core simulation using the [MATSim](https://matsim.org/) framework (version 2025.0).
    - **Python (3.x)**: Data preprocessing pipeline (OSM data extraction, POI classification, population generation) and post-simulation analysis.
    - **Maven**: Java dependency management and build system.
    - **Coordinate System**: `EPSG:32647` (WGS 84 / UTM zone 47N).

## 📂 Key Directory Structure
- `src/main/java`: Java source code for MATSim runners, network converters, and signal modules.
- `pipeline/`: Python scripts for data preparation.
- `data/`: Configuration files (`config.xml`) and traffic condition data.
- `output/`: Default directory for simulation results (events, plans).
- `evaluation/`: Scripts for validating simulation results against real-world data.
- `scenarios/`: MATSim scenario definitions.

## 🚀 Execution Workflow

### 1. Preprocessing (Python)
Prepares the road network and agent population plans.
```bash
cd pipeline
python3 main.py
```
*Note: Requires `pipeline/data/final_trips.csv` and `pipeline/data/subdistricts_180.geojson`.*

### 2. Network Preparation (Java)
Converts OSM data to MATSim format and ensures network connectivity.
```bash
./mvnw exec:java -Dexec.mainClass="org.matsim.project.ConvertOSM"
./mvnw exec:java -Dexec.mainClass="org.matsim.project.RunNetworkCleaner"
```

### 3. Running the Simulation (Java)
Execute the simulation with or without adaptive signals.
- **Standard (Hermes engine)**:
  ```bash
  ./mvnw exec:java -Dexec.mainClass="org.matsim.project.RunMatsim"
  ```
- **Adaptive Signals (Lämmer)**:
  ```bash
  ./mvnw exec:java -Dexec.mainClass="org.matsim.project.RunLaemmerSimulation"
  ```

## 🖥️ Graphical User Interfaces (GUI)

### 1. Configuration Launcher (Python)
A modern interface to edit `config.json` and pick the simulation bounding box on a map.
```bash
python3 gui.py
```
*Requirements: `pip install customtkinter pywebview`*

### 2. MATSim GUI (Java)
The standard MATSim control panel for managing runs and configurations.
```bash
./mvnw exec:java -Dexec.mainClass="org.matsim.gui.MATSimGUI"
```
Alternatively, build and run the executable JAR:
```bash
./mvnw clean package
java -jar target/matsim-example-project-0.0.1-SNAPSHOT.jar
```

## ⚙️ Configuration
- `config.json`: Global settings (Bounding box, sample size, file paths).
- `data/config.xml`: MATSim-specific configuration (scoring, iterations, threads, mobsim settings).
- `pom.xml`: Java dependencies and main class definitions.

## 🛠️ Development Conventions
- **Java**: Follows MATSim API patterns. Key entry points are in `org.matsim.project`.
- **Python**: Modular scripts in `pipeline/` and `evaluation/`. Use `requirements.txt` for environment setup.
- **Testing**: Java tests are located in `src/test/java`. Run with `./mvnw test`.
- **Visualization**: Use [SimWrapper](https://vsp.berlin/simwrapper/) to visualize `output/` files. Always set the coordinate system to `EPSG:32647`.

## 📝 Troubleshooting
- **Disconnected Links**: If the simulation crashes due to agents being "stuck" or no route found, re-run `RunNetworkCleaner`.
- **Memory**: Simulation is memory-intensive. Adjust `maven_opts` in `config.json` or use `-Xmx16G` in your shell.
