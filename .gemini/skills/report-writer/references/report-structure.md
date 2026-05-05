# Report Structure & Content Mapping

- **Introduction**: Focus on the scope (Pathum Wan district) and the goal of integrating an activity-based model with adaptive signals.
- **Methodology - Preprocessing**: Detail the Python pipeline (`pipeline/main.py`). Mention OSM extraction and POI classification.
- **Methodology - Demand Generation**: Detail `pipeline/generate_plans.py`, specifically the coordinate projection to EPSG:32647 and the temporal jittering applied to trips.
- **Methodology - Simulation**: Detail the Lämmer algorithm (`documents/laemmer_algorithm.md`) and how it scales using the `ThrottledSignalEngine`.
- **Validation**: Detail the metrics evaluated in the `evaluation/` directory (spatial accuracy, link usage).
