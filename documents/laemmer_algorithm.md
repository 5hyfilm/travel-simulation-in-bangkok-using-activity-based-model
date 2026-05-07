# How Lämmer Adaptive Signal Control Works

Reference: *Lämmer, S. & Helbing, D. (2008). Self-control of traffic lights and vehicle flows in urban road networks.*

---

## 1. Fixed-time Signals vs Lämmer

### Fixed-time Signals (conventional)
Most traffic lights in the world operate on a **fixed cycle**:

```
Green 30s → Red 30s → Green 30s → Red 30s → ...
```

The problem is that timing ignores how many vehicles are actually waiting — the clock keeps running even when the road is empty.

### Lämmer Signals (Adaptive)
Lämmer operates with **no fixed cycle**. Each intersection independently decides which direction gets a green phase and for how long, based on the actual number of waiting vehicles at that moment.

---

## 2. Core Concept: Queue Pressure

Lämmer treats each incoming link (a road leading toward an intersection) like a pipe accumulating fluid.

The **pressure** of each incoming link is proportional to:
- **Arrival rate** λ (lambda) — vehicles arriving per second
- **Road capacity** (saturation flow) s — vehicles that can pass per second when green

```
Pressure ∝ λ / s
```

If a road has a high arrival rate but slow discharge → high pressure → it should receive green first.

---

## 3. Two Modes of Lämmer

Lämmer alternates between two operating modes depending on conditions:

### Mode 1: Spontaneous (demand-responsive)

Under normal conditions Lämmer always **opens the green phase for the direction with the highest pressure**.

```
Every calculation cycle:
  → Compute pressure for every incoming link
  → Select the link with the highest pressure
  → Open green for that link
  → Wait until pressure drops or another link becomes more urgent
```

Advantage: responds immediately when traffic is dense in any one direction.

### Mode 2: Stabilizing (starvation prevention)

The problem with Mode 1 is that if a major road is always busy, minor roads may never receive a green phase → **deadlock (starvation)**.

Lämmer addresses this with **Stabilizing Mode**: when any link has been waiting longer than a defined threshold (`regulationTime`), the system forces that link to receive a green phase first, even if it does not have the highest pressure at that moment.

```
If any link has waited longer than regulationTime:
  → Enter Stabilizing mode
  → Force that link to receive green first
  → Return to Spontaneous mode afterwards
```

---

## 4. What Happens Each Cycle

```
┌─────────────────────────────────────────────┐
│              One intersection               │
│                                             │
│  Every N seconds (default: 5 seconds):      │
│                                             │
│  1. Count queued vehicles per direction     │
│  2. Compute pressure (λ/s) per link         │
│  3. Check if any link has waited too long   │
│     → Yes: Stabilizing mode                 │
│     → No:  Spontaneous mode                 │
│  4. Select link to receive green            │
│  5. Open green, wait interGreenTime, switch │
└─────────────────────────────────────────────┘
```

### What is interGreenTime?

The period during which all directions are stopped simultaneously (all-red / amber) before switching phases — a safety buffer to prevent vehicles from colliding in the intersection.

---

## 5. Key Lämmer Parameters

| Parameter | Meaning | Typical default |
|-----------|---------|----------------|
| `desiredCycleTime` | Target average cycle length used as a reference in calculations | ~90 seconds |
| `regulationTime` | Maximum wait time for a link before entering stabilizing mode | ~X seconds |
| `interGreenTime` | All-red time between phase switches | ~5 seconds |
| `minGreenTime` | Minimum green duration to prevent rapid flickering | ~5 seconds |

This project uses all MATSim 2025.0 defaults (no custom values set).

---

## 6. Why Is It Called "Self-organizing"?

Lämmer is a **decentralised algorithm** — each intersection makes its own decisions based solely on the vehicles near it; there is no central controller.

The emergent result is that when many intersections operate this way simultaneously, a **Green Wave** forms — consecutive green phases across multiple intersections arise automatically without any pre-programming.

```
Intersection A → opens green northbound
Vehicles arrive at intersection B → B opens green northbound just in time
Vehicles arrive at intersection C → ... (emerges on its own)
```

---

## 7. Integration with MATSim in This Project

```
MATSim QSim (simulation engine)
         │
         │  Every 5 seconds (ThrottledSignalEngine)
         ▼
LaemmerSignalController.updateState()
         │
         ├── Read queue counts from QSim
         ├── Compute pressure per SignalGroup
         ├── Decide (Spontaneous or Stabilizing)
         └── Call setSignalState(GREEN/RED) back to QSim
```

### ThrottledSignalEngine

If Lämmer recalculates every simulation step (every second) it becomes too costly for large simulations. This project adds `ThrottledSignalEngine` as a throttle so Lämmer only recalculates **every 5 seconds**.

```java
ThrottledSignalEngine.setUpdateInterval(5); // adjustable in RunLaemmerSimulation.java
```

Lower value → more accurate, but slower  
Higher value → faster, but signals respond more slowly

---

## 8. Limitations of Lämmer

1. **Requires accurate capacity data** — if road capacities in the network do not match reality, pressure calculations will be inaccurate.

2. **Direction-unaware** — in this project each SignalGroup controls one full incoming link. Lämmer cannot distinguish left-turning from straight-ahead vehicles (no `lanes.xml`).

3. **Simulation time ≠ real time** — vehicles in simulation follow shortest paths perfectly with no risky behaviour, so results will be better than real-world conditions.

4. **QSim only** — `LaemmerSignalController` reads queue data directly from `QSimSignalEngine`, and `ThrottledSignalEngine` wraps `QSimSignalEngine`. Therefore **Hermes cannot be used** (the faster alternative engine), because the entire MATSim signals contrib is designed for QSim only. Using Hermes requires disabling the signal system.

---

## 9. Further Reading

- Original paper: `paper/Implementing an adaptive traffic signal.pdf`
- Signal placement code: `docs/signal_placement.md`
- Run guide: `MANUAL.md`
- MATSim Signals contrib: `org.matsim.contrib.signals.controller.laemmerFix`
- Engine comparison: `documents/qsim_vs_hermes.md`
