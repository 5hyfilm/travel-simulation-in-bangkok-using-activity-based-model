---
name: matsim-bangkok
description: Manage the MATSim Bangkok simulation lifecycle, including data preprocessing, network conversion, simulation execution, and evaluation. Use when the user wants to run or debug the Bangkok travel simulation.
---

# MATSim Bangkok Skill

This skill provides the procedural knowledge required to manage the MATSim-based travel simulation for Bangkok.

## Quick Start

- **Full Workflow**: Follow the sequence in [workflow.md](references/workflow.md).
- **Run Simulation**: `./mvnw exec:java -Dexec.mainClass="org.matsim.project.RunMatsim"`
- **Adaptive Signals**: `./mvnw exec:java -Dexec.mainClass="org.matsim.project.RunLaemmerSimulation"`

## Key Capabilities

### 1. Data Pipeline
The simulation relies on a Python-based pipeline to process OSM data and generate population plans.
- **Reference**: See `pipeline/` directory and [workflow.md](references/workflow.md).

### 2. Java MATSim Integration
The core simulation uses Java.
- **Main Classes**: `RunMatsim`, `RunLaemmerSimulation`, `ConvertOSM`, `RunNetworkCleaner`.
- **Build System**: Maven (`mvnw`).

### 3. Troubleshooting
- **Memory**: Increase heap size with `MAVEN_OPTS="-Xmx16G"`.
- **Network Errors**: Run `RunNetworkCleaner` if agents cannot find routes.

## Resources

- [Workflow Guide](references/workflow.md): Detailed step-by-step instructions for the simulation pipeline.
