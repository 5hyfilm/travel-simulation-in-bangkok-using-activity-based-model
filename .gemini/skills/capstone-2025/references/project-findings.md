# Project Findings and Technical Data

Use these specific statistics and details for technical accuracy in the report.

## 1. System Overview & Performance
- **Framework**: Integration of ActivitySim (Macro/Brain) and MATSim (Micro/Physical World).
- **Scale**: Simulates **300,000 agents** and **700,000 trips** for Greater Bangkok.
- **Workflow Efficiency**: Automation reduced the preprocessing pipeline from **7 steps to 2 steps**.
- **Preprocessing Speed**: Trip processing (trip.csv → plan.xml) takes approximately **7 minutes**.
- **Simulation Speed**: Using the **Hermes engine** reduces simulation time by **70%** compared to the default QSim engine.
- **Hardware Specs**: Recommended 8-core CPU, 25GB free RAM (note: 900k agents would require 64GB).

## 2. Methodology Details
- **Spatial System**: Based on the **180-subdistrict system** used by the Bangkok Metropolitan Administration (BMA).
- **Coordinate System**: UTM (meters) for physical simulation; converted to/from WGS84 for validation.
- **Activity Classification**: Logic-based heuristic maps OSM tags (amenity, shop, etc.) into **10 categories**: Home, Work, Shopping, Education, Dining, Public Service, Park, Leisure, Religion, Transit.
- **Location Assignment**: Fixed locations for Home, Work, and Education; random assignment for secondary activities within the TAZ.
- **Temporal Realism**: Applied **±30 minutes of time jittering** to departures to prevent artificial traffic spikes.

## 3. Adaptive Signal Control (Lämmer)
- **Algorithm**: Decentralized control with two regimes:
    - **Optimizing Regime**: Minimizes total waiting time based on a priority index.
    - **Stabilizing Regime**: Intervenes to prevent starvation on minor roads when maximum wait times are exceeded.
- **Challenge**: Dynamic signal calculation for 300k agents is computationally intensive (OOM risk).

## 4. Results and Validation
- **Data Integrity**: **100% Integrity** achieved (zero data loss and no "ghost" agents).
- **Spatial Accuracy**: **94.63% Accuracy Rate** (5% variance due to "POI Scarcity" in OSM).
- **Simulation Fidelity**: 
    - Benchmarked against **Google Maps Routes API** (30 pairs, 3 time windows).
    - **62 of 89 routes** passed within ±35% of real travel times.
    - **Mean Absolute Percentage Error (MAPE)**: 25.6%.
    - **Mean Absolute Error (MAE)**: 6.8 minutes.
    - *Finding*: Agents generally move slightly faster than real-world traffic.

## 5. Future Work
- Integration of the **MATSim Emissions Extension** to calculate localized CO2 and PM2.5 levels.
