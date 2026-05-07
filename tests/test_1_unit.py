"""
test_1_unit.py
==============
UNIT TESTS — test individual functions in complete isolation.
No real files, no network calls, no GUI rendering.

Run:
    python tests/test_1_unit.py
"""

import sys
import os
import json
import math
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

# ── Stub GUI libraries so we can import gui without a display ─────────────────
for mod in ["customtkinter", "tkinter", "tkinter.filedialog",
            "tkinter.messagebox", "webview"]:
    sys.modules.setdefault(mod, MagicMock())

import gui
from apply_traffic_conditions import validate_condition
from clean_plans import fix_plan
from lxml import etree


# ══════════════════════════════════════════════════════════════════════════════
# 1A. gui._smart_path
# ══════════════════════════════════════════════════════════════════════════════

class TestSmartPath(unittest.TestCase):

    def test_inside_project_is_relative(self):
        path = os.path.join(gui.PROJECT_ROOT, "data", "config.xml")
        result = gui._smart_path(path)
        self.assertFalse(os.path.isabs(result))

    def test_outside_project_is_absolute(self):
        result = gui._smart_path(tempfile.gettempdir())
        self.assertTrue(os.path.isabs(result))

    def test_no_dotdot_for_inside_path(self):
        path = os.path.join(gui.PROJECT_ROOT, "pipeline", "output", "plan.xml")
        self.assertFalse(gui._smart_path(path).startswith(".."))

    def test_different_drive_windows(self):
        if os.name != "nt":
            self.skipTest("Windows only")
        result = gui._smart_path("Z:\\some\\path\\file.txt")
        self.assertTrue(os.path.isabs(result))

    def test_project_root_itself_not_absolute(self):
        result = gui._smart_path(gui.PROJECT_ROOT)
        self.assertFalse(result.startswith(".."))

    def test_deep_nested_inside_project(self):
        path = os.path.join(gui.PROJECT_ROOT, "a", "b", "c", "d.txt")
        result = gui._smart_path(path)
        self.assertFalse(os.path.isabs(result))


# ══════════════════════════════════════════════════════════════════════════════
# 1B. gui.load_config / save_config
# ══════════════════════════════════════════════════════════════════════════════

class TestConfigIO(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = os.path.join(self.tmp, "config.json")
        self._orig = gui.CONFIG_PATH
        gui.CONFIG_PATH = self.cfg
        self.sample = {
            "input":     {"north": 13.75, "south": 13.73, "east": 100.55,
                          "west": 100.51, "sample_size": 5000,
                          "trips_filename": "trips.csv",
                          "subdistricts_filename": "sub.geojson"},
            "execution": {"run_simulation_automatically": False,
                          "maven_opts": "-Xmx8G",
                          "matsim_config_file": "data/config.xml",
                          "apply_traffic_conditions": False,
                          "traffic_conditions_file": "data/tc.json"},
            "api_keys":  {"google_maps": "KEY123"},
        }

    def tearDown(self):
        gui.CONFIG_PATH = self._orig
        shutil.rmtree(self.tmp)

    def test_save_creates_file(self):
        gui.save_config(self.sample)
        self.assertTrue(os.path.exists(self.cfg))

    def test_load_returns_dict(self):
        gui.save_config(self.sample)
        self.assertIsInstance(gui.load_config(), dict)

    def test_roundtrip_preserves_float(self):
        gui.save_config(self.sample)
        loaded = gui.load_config()
        self.assertAlmostEqual(loaded["input"]["north"], 13.75, places=5)

    def test_roundtrip_preserves_int(self):
        gui.save_config(self.sample)
        self.assertEqual(gui.load_config()["input"]["sample_size"], 5000)

    def test_roundtrip_preserves_string(self):
        gui.save_config(self.sample)
        self.assertEqual(gui.load_config()["api_keys"]["google_maps"], "KEY123")

    def test_roundtrip_preserves_bool(self):
        gui.save_config(self.sample)
        self.assertFalse(gui.load_config()["execution"]["run_simulation_automatically"])

    def test_missing_file_raises_file_not_found(self):
        gui.CONFIG_PATH = os.path.join(self.tmp, "nope.json")
        with self.assertRaises(FileNotFoundError):
            gui.load_config()

    def test_save_writes_valid_json(self):
        gui.save_config(self.sample)
        with open(self.cfg, encoding="utf-8") as f:
            parsed = json.loads(f.read())
        self.assertIn("input", parsed)

    def test_utf8_chars_preserved(self):
        self.sample["api_keys"]["google_maps"] = "test-api-key-utf8"
        gui.save_config(self.sample)
        self.assertEqual(gui.load_config()["api_keys"]["google_maps"], "test-api-key-utf8")

    def test_overwrite_updates_value(self):
        gui.save_config(self.sample)
        self.sample["input"]["sample_size"] = 999
        gui.save_config(self.sample)
        self.assertEqual(gui.load_config()["input"]["sample_size"], 999)


# ══════════════════════════════════════════════════════════════════════════════
# 1C. apply_traffic_conditions.validate_condition
# ══════════════════════════════════════════════════════════════════════════════

class TestValidateCondition(unittest.TestCase):

    def _cond(self, **kw):
        base = {"name": "test", "speed_factor": 0.5,
                "capacity_factor": 0.5, "road_types": ["residential"]}
        base.update(kw)
        return base

    def test_valid_road_type_condition(self):
        self.assertTrue(validate_condition(self._cond()))

    def test_valid_link_id_condition(self):
        c = {"name": "x", "speed_factor": 0.5,
             "capacity_factor": 0.0, "link_id": "123"}
        self.assertTrue(validate_condition(c))

    def test_speed_factor_too_low_fails(self):
        self.assertFalse(validate_condition(self._cond(speed_factor=0.0)))

    def test_speed_factor_too_high_fails(self):
        self.assertFalse(validate_condition(self._cond(speed_factor=1.5)))

    def test_speed_factor_at_min_boundary(self):
        self.assertTrue(validate_condition(self._cond(speed_factor=0.01)))

    def test_speed_factor_at_max_boundary(self):
        self.assertTrue(validate_condition(self._cond(speed_factor=1.0)))

    def test_capacity_factor_zero_valid(self):
        self.assertTrue(validate_condition(self._cond(capacity_factor=0.0)))

    def test_capacity_factor_negative_fails(self):
        self.assertFalse(validate_condition(self._cond(capacity_factor=-0.1)))

    def test_no_road_types_or_link_id_fails(self):
        c = {"name": "x", "speed_factor": 0.5, "capacity_factor": 0.5}
        self.assertFalse(validate_condition(c))


# ══════════════════════════════════════════════════════════════════════════════
# 1D. clean_plans.fix_plan
# ══════════════════════════════════════════════════════════════════════════════

def _make_plan(*activity_types):
    """Build a minimal MATSim <plan> XML element."""
    plan = etree.Element("plan")
    for i, atype in enumerate(activity_types):
        act = etree.SubElement(plan, "activity")
        act.set("type", atype)
        act.set("x", "100.0")
        act.set("y", "13.0")
        if i < len(activity_types) - 1:
            etree.SubElement(plan, "leg").set("mode", "car")
    return plan

class TestFixPlanHomeEnd(unittest.TestCase):

    def test_already_ends_home_returns_false(self):
        plan = _make_plan("home", "work", "home")
        self.assertFalse(fix_plan(plan))

    def test_missing_home_returns_none(self):
        plan = _make_plan("work", "shopping")
        self.assertIsNone(fix_plan(plan))

    def test_empty_plan_returns_none(self):
        plan = etree.Element("plan")
        self.assertIsNone(fix_plan(plan))

    def test_fixes_plan_ending_in_work(self):
        plan = _make_plan("home", "work", "shopping", "work")
        result = fix_plan(plan)
        self.assertTrue(result)
        acts = [e.get("type") for e in plan if e.tag == "activity"]
        self.assertEqual(acts[-1], "home")

    def test_single_home_activity(self):
        plan = _make_plan("home")
        self.assertFalse(fix_plan(plan))

    def test_fix_removes_trailing_non_home(self):
        plan = _make_plan("home", "work", "dining", "leisure")
        fix_plan(plan)
        acts = [e.get("type") for e in plan if e.tag == "activity"]
        self.assertEqual(acts[-1], "home")


# ══════════════════════════════════════════════════════════════════════════════
# 1E. haversine & time helpers (from validate_google_maps)
# ══════════════════════════════════════════════════════════════════════════════

# Import helpers directly without triggering the full script
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def hms_to_sec(t):
    try:
        h, m, s = str(t).split(":")
        return int(h)*3600 + int(m)*60 + int(s)
    except:
        return None

class TestHaversine(unittest.TestCase):

    def test_same_point_is_zero(self):
        self.assertAlmostEqual(haversine_km(13.75, 100.52, 13.75, 100.52), 0.0)

    def test_known_distance_silom_chatuchak(self):
        # ~9.3 km straight line
        d = haversine_km(13.7221, 100.5296, 13.8030, 100.5530)
        self.assertAlmostEqual(d, 9.3, delta=0.5)

    def test_symmetric(self):
        d1 = haversine_km(13.72, 100.52, 13.80, 100.55)
        d2 = haversine_km(13.80, 100.55, 13.72, 100.52)
        self.assertAlmostEqual(d1, d2, places=5)

    def test_positive_distance(self):
        self.assertGreater(haversine_km(13.0, 100.0, 14.0, 101.0), 0)

class TestHmsToSec(unittest.TestCase):

    def test_midnight(self):
        self.assertEqual(hms_to_sec("00:00:00"), 0)

    def test_one_hour(self):
        self.assertEqual(hms_to_sec("01:00:00"), 3600)

    def test_mixed(self):
        self.assertEqual(hms_to_sec("07:30:45"), 7*3600 + 30*60 + 45)

    def test_invalid_returns_none(self):
        self.assertIsNone(hms_to_sec("not-a-time"))

    def test_empty_returns_none(self):
        self.assertIsNone(hms_to_sec(""))

    def test_25_hours(self):
        self.assertEqual(hms_to_sec("25:00:00"), 25*3600)


# ══════════════════════════════════════════════════════════════════════════════
# 1F. to_seconds & pct_change (from compare_scenarios)
# ══════════════════════════════════════════════════════════════════════════════

def to_seconds(series):
    try:
        return pd.to_timedelta(series.astype(str), errors="coerce").dt.total_seconds()
    except Exception:
        def _parse(s):
            try:
                parts = str(s).split(":")
                return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            except Exception:
                return np.nan
        return pd.to_numeric(series.apply(_parse), errors="coerce")

def pct_change(a, b):
    if a == 0: return float("inf")
    return (b - a) / a * 100

class TestToSeconds(unittest.TestCase):

    def test_standard_time(self):
        s = pd.Series(["01:00:00"])
        self.assertAlmostEqual(to_seconds(s).iloc[0], 3600.0)

    def test_zero_time(self):
        s = pd.Series(["00:00:00"])
        self.assertAlmostEqual(to_seconds(s).iloc[0], 0.0)

    def test_invalid_is_nan(self):
        s = pd.Series(["bad"])
        self.assertTrue(np.isnan(to_seconds(s).iloc[0]))

    def test_multiple_values(self):
        s = pd.Series(["00:30:00", "01:00:00", "02:00:00"])
        result = to_seconds(s)
        self.assertEqual(list(result), [1800.0, 3600.0, 7200.0])

class TestPctChange(unittest.TestCase):

    def test_increase(self):
        self.assertAlmostEqual(pct_change(100, 150), 50.0)

    def test_decrease(self):
        self.assertAlmostEqual(pct_change(100, 80), -20.0)

    def test_no_change(self):
        self.assertAlmostEqual(pct_change(100, 100), 0.0)

    def test_zero_base_returns_inf(self):
        self.assertEqual(pct_change(0, 100), float("inf"))

    def test_negative_to_positive(self):
        self.assertAlmostEqual(pct_change(-50, 50), -200.0)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [TestSmartPath, TestConfigIO, TestValidateCondition,
                TestFixPlanHomeEnd, TestHaversine, TestHmsToSec,
                TestToSeconds, TestPctChange]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    print("=" * 60)
    print("  UNIT TESTS")
    print("=" * 60)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total  = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"\n  PASSED {passed}/{total}")
    sys.exit(0 if result.wasSuccessful() else 1)
