# QSim vs Hermes: MATSim Simulation Engines

MATSim offers two main simulation engines, each with different speed and feature trade-offs.

---

## Overview

| Property | QSim | Hermes |
|----------|------|--------|
| **Type** | Queue-based simulation | Event-driven simulation |
| **Speed** | Slower | Faster (better suited for large agent populations) |
| **Memory** | Higher usage | More efficient |
| **Traffic dynamics** | Queue / Kinematic waves | Queue only |
| **Signals / Lämmer** | Supported ✅ | Not supported ❌ |
| **Lanes** | Supported ✅ | Not supported ❌ |
| **Replanning** | Supported ✅ | Supported ✅ |
| **Public transit** | Supported ✅ | Supported ✅ |
| **Best for** | Simulations requiring signals / lanes | Large-scale simulations prioritising speed |

---

## Hermes Is Faster but Has Fewer Features

Hermes is simply a faster simulation runner — **it does not change how MATSim works**. Replanning and iterations function exactly the same; each iteration just completes more quickly.

The trade-off is that Hermes does not support the full signals contrib (`org.matsim.contrib.signals`). If Lämmer or lane-based simulation is required, QSim must be used.

---

## Iterations Are Independent of the Engine

**Iterations** and the **engine** are separate concepts:

- **Engine** (QSim / Hermes) = how vehicles move through the simulation each iteration
- **Iteration** = one cycle of agent behaviour adjustment

Regardless of which engine is used, the number of iterations needed for the system to converge remains the same — Hermes simply makes each iteration **finish faster**.

---

## What Is a MATSim Iteration?

**1 iteration = 1 simulated day** — each iteration has 2 steps:

```
Iteration N
├── 1. Simulation (QSim or Hermes)
│       All vehicles travel according to their current plan
│       Events are recorded (red light stops, arrivals, etc.)
│
└── 2. Replanning
        Each agent decides whether to change behaviour
        e.g. reroute (ReRoute) if the current path was congested
        → produces a new plan for Iteration N+1
```

The goal is for the system to **converge to equilibrium** — every agent has chosen the best route for themselves and no one benefits from switching.

---

## Iteration ≠ Machine Learning

Although they look similar, the principles are different:

| | MATSim Iteration | Machine Learning |
|--|-----------------|-----------------|
| **Mechanism** | Trial and error | Learn from error, update weights |
| **Memory** | No accumulated knowledge across rounds | Model accumulates knowledge across epochs |
| **Goal** | Find equilibrium | Minimise loss function |
| **When conditions change** | Must re-run from scratch | Model may generalise |
| **Convergence** | Yes — no benefit to running beyond convergence | Watch for overfitting |

---

## What This Project Uses

This project uses **QSim** and runs **0 iterations** (`setLastIteration(0)`) because:
- Lämmer adaptive signals are required → QSim is mandatory
- 0 iterations = a single simulation pass with no replanning, suitable for quickly observing initial traffic signal behaviour

---

## Further Reading

- Lämmer algorithm: `documents/laemmer_algorithm.md`
- Run guide: `MANUAL.md`
