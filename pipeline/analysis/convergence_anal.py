"""
convergence_anal.py
===================
Check whether the MATSim simulation converged properly by analysing
iteration-by-iteration score, distance, and stability trends.

Reads:
  output/scorestats.csv          — avg score per iteration
  output/traveldistancestats.csv — avg trip distance per iteration

Run from project root:
  python pipeline/analysis/convergence_anal.py
"""

import pandas as pd

SCORE_FILE    = "output/scorestats.csv"
DIST_FILE     = "output/traveldistancestats.csv"
WINDOW        = 5   # rolling window for stability check

# ── Load ───────────────────────────────────────────────────────────────────
scores = pd.read_csv(SCORE_FILE, sep=";")
dists  = pd.read_csv(DIST_FILE,  sep=";")
dists.columns = [c.strip() for c in dists.columns]

n_iter = scores["iteration"].max()

print("=" * 65)
print("  Convergence Analysis — MATSim Simulation")
print("=" * 65)
print(f"  Iterations run : {n_iter}")
print()

# ── Score trajectory (every 5 iterations) ─────────────────────────────────
print("─" * 65)
print("  Score progression (avg_executed = score agents actually used)")
print("─" * 65)
print(f"  {'Iter':>5}  {'Executed':>10}  {'Best':>10}  {'Worst':>10}  {'Trend'}")
print(f"  {'─'*5}  {'─'*10}  {'─'*10}  {'─'*10}")

prev_exec = None
for _, row in scores.iterrows():
    it = int(row["iteration"])
    if it % 5 == 0 or it == n_iter:
        exec_score = row["avg_executed"]
        trend = ""
        if prev_exec is not None:
            delta = exec_score - prev_exec
            trend = f"{'▲' if delta > 0 else '▼'} {abs(delta):.2f}"
        print(f"  {it:>5}  {exec_score:>10.2f}  {row['avg_best']:>10.2f}  "
              f"{row['avg_worst']:>10.2f}  {trend}")
        prev_exec = exec_score

# ── Stability in last N iterations ────────────────────────────────────────
last = scores[scores["iteration"] > n_iter - WINDOW]["avg_executed"]
score_std  = last.std()
score_mean = last.mean()
score_range = last.max() - last.min()

print()
print(f"  Last {WINDOW} iterations — avg_executed:")
print(f"    Mean  : {score_mean:.3f}")
print(f"    Std   : {score_std:.3f}")
print(f"    Range : {score_range:.3f}  (last={last.iloc[-1]:.3f}, prev={last.iloc[-2]:.3f})")

if score_std < 1.0:
    verdict = "✅ CONVERGED  — score is stable"
elif score_std < 5.0:
    verdict = "⚠️  UNSTABLE   — score still fluctuating, needs more iterations"
else:
    verdict = "❌ NOT CONVERGED — score is highly unstable"
print(f"\n  Verdict: {verdict}")

# ── Distance trajectory ────────────────────────────────────────────────────
print()
print("─" * 65)
print("  Avg trip distance progression (km)")
print("─" * 65)
print(f"  {'Iter':>5}  {'Avg dist (km)':>14}  {'Trend'}")
print(f"  {'─'*5}  {'─'*14}")

dist_col = [c for c in dists.columns if "Trip" in c][0]
prev_d = None
for _, row in dists.iterrows():
    it = int(row["ITERATION"])
    if it % 5 == 0 or it == n_iter:
        d = row[dist_col] / 1000
        trend = ""
        if prev_d is not None:
            delta = d - prev_d
            trend = f"{'▲' if delta > 0 else '▼'} {abs(delta*1000):.0f}m"
        print(f"  {it:>5}  {d:>14.3f}  {trend}")
        prev_d = d

last_d = dists[dists["ITERATION"] > n_iter - WINDOW][dist_col] / 1000
dist_std = last_d.std()
print(f"\n  Last {WINDOW} iter std: {dist_std:.4f} km  "
      f"({'✅ stable' if dist_std < 0.1 else '⚠️  still shifting'})")

# ── Score gap: best vs executed ────────────────────────────────────────────
print()
print("─" * 65)
print("  Score gap: best vs executed (gap → 0 means good plan selection)")
print("─" * 65)
scores["gap"] = scores["avg_best"] - scores["avg_executed"]
print(f"  {'Iter':>5}  {'Executed':>10}  {'Best':>10}  {'Gap':>8}")
print(f"  {'─'*5}  {'─'*10}  {'─'*10}  {'─'*8}")
for _, row in scores.iterrows():
    it = int(row["iteration"])
    if it % 10 == 0 or it == n_iter:
        print(f"  {it:>5}  {row['avg_executed']:>10.2f}  {row['avg_best']:>10.2f}  "
              f"{row['gap']:>8.2f}")

final_gap = scores[scores["iteration"] == n_iter]["gap"].values[0]
print(f"\n  Final gap at iter {n_iter}: {final_gap:.2f}")
if final_gap < 2.0:
    print("  ✅ Agents are executing close to their best-known plan")
elif final_gap < 10.0:
    print("  ⚠️  Moderate gap — some agents are not executing their best plan")
else:
    print("  ❌ Large gap — agents frequently diverge from their best plan")

# ── Full score table (all iterations) ─────────────────────────────────────
print()
print("─" * 65)
print("  Full score table")
print("─" * 65)
print(scores[["iteration","avg_executed","avg_best","avg_worst"]].to_string(index=False))
