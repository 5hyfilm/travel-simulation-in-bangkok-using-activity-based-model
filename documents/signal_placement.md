# Signal Placement in the Bangkok Lämmer Simulation

Describes how this project determines the location and structure of traffic signals for use with the Lämmer adaptive signal controller in MATSim.

---

## Overview

Traffic signals are generated automatically from the road network topology during the `ConvertOSM` step. The project does not use the `highway=traffic_signals` OSM tag directly — instead it applies a topology-based criterion.

---

## Junction Selection Criteria

Any junction that meets the following condition receives a traffic signal:

```
(number of incoming links) + (number of outgoing links) > 3
and has at least 1 incoming link
```

**Rationale:** junctions with a combined degree greater than 3 are typically real intersections where traffic flows cross, making signal control appropriate. Nodes with degree ≤ 3 are usually simple turns or straightforward road connections.

**Limitation:** this approach may place signals at junctions that have none in reality, and may miss junctions that do have signals but have degree ≤ 3.

---

## Signal Structure

For each qualifying junction, the system creates data at 3 levels:

### 1. Signal System (Junction level)
- 1 junction → 1 `SignalSystem`
- Uses the junction's **Node ID** as the System ID

### 2. Signal (Link level)
- Each **incoming link** → 1 `Signal`
- The Signal references the link that vehicles travel to reach that junction
- Uses the **Link ID** as the Signal ID

### 3. Signal Group (Phase level)
- Each Signal → 1 separate `SignalGroup` (1 group per incoming direction)
- Allows Lämmer to control each incoming direction independently

**Example:** a junction with 3 incoming links receives 1 SignalSystem, 3 Signals, and 3 SignalGroups

```
Junction Node (id: 12345)
├── SignalSystem: "12345"
│   ├── Signal: "link_A"  → group "12345_1"
│   ├── Signal: "link_B"  → group "12345_2"
│   └── Signal: "link_C"  → group "12345_3"
```

---

## Generated Files

`ConvertOSM.java` creates 3 files in `data/processed/`:

| File | Content |
|------|---------|
| `signalSystems.xml` | Defines which SignalSystem exists at each junction and which Signals are on which links |
| `signalGroups.xml` | Groups Signals into SignalGroups by phase |
| `signalControl.xml` | Sets the controller to `LaemmerSignalController` for every system |

---

## Cleaning Signals Before Running Simulation

When `RunNetworkCleaner` removes disconnected links from the network, some Signals may still reference links that no longer exist in the cleaned network.

`RunLaemmerSimulation.java` therefore calls `cleanSignals()` automatically before running the simulation, in 3 steps:

1. **Remove Signals** that reference links missing from the network
2. **Remove SignalSystems** that have no Signals remaining
3. **Remove SignalGroups** that are empty or belong to a removed system

> **Note:** whenever the network is rebuilt or modified, `ConvertOSM` and `RunNetworkCleaner` must be re-run, because the signal XML files will still reference the old set of links.

---

## Lämmer Controller

Every SignalSystem uses `LaemmerSignalController`, an adaptive algorithm that:
- Calculates the "pressure" of queued vehicles on each incoming link in real-time
- Opens the green phase for the direction with the highest pressure first
- Adjusts green time automatically — no fixed schedule

The calculation frequency can be configured in `RunLaemmerSimulation.java`:
```java
ThrottledSignalEngine.setUpdateInterval(5); // update every 5 seconds (default)
```

---

## Related Files

| File | Role |
|------|------|
| `src/main/java/org/matsim/project/ConvertOSM.java` | Generates signal XML from OSM topology |
| `src/main/java/org/matsim/project/RunLaemmerSimulation.java` | Loads, cleans, and runs the simulation |
| `src/main/java/org/matsim/contrib/signals/builder/ThrottledSignalEngine.java` | Controls the signal update frequency |
| `data/processed/signalSystems.xml` | Signal positions at each junction |
| `data/processed/signalGroups.xml` | Signal groupings by phase |
| `data/processed/signalControl.xml` | Sets the controller to Lämmer |
