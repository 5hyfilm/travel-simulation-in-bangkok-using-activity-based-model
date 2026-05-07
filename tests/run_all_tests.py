"""
run_all_tests.py
================
Run all three test levels and print a combined report.

    python tests/run_all_tests.py
"""

import sys
import os
import unittest
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_1_unit        import *   # noqa
from test_2_integration import *   # noqa
from test_3_e2e         import *   # noqa

LEVELS = [
    ("1 · UNIT",        ["TestSmartPath", "TestConfigIO", "TestValidateCondition",
                          "TestFixPlanHomeEnd", "TestHaversine", "TestHmsToSec",
                          "TestToSeconds", "TestPctChange"]),
    ("2 · INTEGRATION", ["TestConfigGuiIntegration",
                          "TestApplyTrafficConditionsIntegration",
                          "TestPipelineDataIntegration"]),
    ("3 · END-TO-END",  ["TestGUIFullSaveWorkflow",
                          "TestTrafficConditionsE2E",
                          "TestSimulationOutputE2E"]),
]

W = 64

def run_level(name, class_names):
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    g = globals()
    for cn in class_names:
        cls = g.get(cn)
        if cls:
            suite.addTests(loader.loadTestsFromTestCase(cls))

    print(f"\n{'─'*W}")
    print(f"  {name}")
    print(f"{'─'*W}")
    t0 = time.time()
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    elapsed = time.time() - t0
    passed  = result.testsRun - len(result.failures) - len(result.errors)
    skipped = len(result.skipped) if hasattr(result, "skipped") else 0
    status  = "✅ PASS" if result.wasSuccessful() else "❌ FAIL"
    print(f"\n  {status}  {passed}/{result.testsRun} passed  "
          f"({skipped} skipped)  {elapsed:.2f}s")
    return result

if __name__ == "__main__":
    print("=" * W)
    print("  Bangkok MATSim — Full Test Suite")
    print("=" * W)

    results = [run_level(name, classes) for name, classes in LEVELS]

    total_run    = sum(r.testsRun for r in results)
    total_passed = sum(r.testsRun - len(r.failures) - len(r.errors) for r in results)
    total_fail   = sum(len(r.failures) + len(r.errors) for r in results)
    total_skip   = sum(len(r.skipped) if hasattr(r, "skipped") else 0 for r in results)

    print(f"\n{'='*W}")
    print(f"  FINAL SUMMARY")
    print(f"{'='*W}")
    for (name, _), r in zip(LEVELS, results):
        icon = "✅" if r.wasSuccessful() else "❌"
        p = r.testsRun - len(r.failures) - len(r.errors)
        print(f"  {icon}  {name:<22}  {p}/{r.testsRun} passed")
    print(f"{'─'*W}")
    print(f"  Total : {total_passed}/{total_run} passed  "
          f"| {total_fail} failed  | {total_skip} skipped")
    print(f"{'='*W}")

    sys.exit(0 if all(r.wasSuccessful() for r in results) else 1)
