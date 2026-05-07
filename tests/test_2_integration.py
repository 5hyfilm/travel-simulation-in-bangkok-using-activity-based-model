"""
test_2_integration.py
=====================
INTEGRATION TESTS — test how multiple components work together
using real project files (read-only copies).

Run:
    python tests/test_2_integration.py
"""

import sys
import os
import json
import gzip
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

for mod in ["customtkinter", "tkinter", "tkinter.filedialog",
            "tkinter.messagebox", "webview"]:
    sys.modules.setdefault(mod, MagicMock())

import gui
from apply_traffic_conditions import load_conditions, apply_conditions


# ══════════════════════════════════════════════════════════════════════════════
# 2A. Config ↔ GUI integration
#     Real config.json → load → validate all keys exist and correct types
# ══════════════════════════════════════════════════════════════════════════════

class TestConfigGuiIntegration(unittest.TestCase):

    def setUp(self):
        self.cfg = gui.load_config()

    def test_real_config_loads(self):
        self.assertIsInstance(self.cfg, dict)

    def test_input_section_has_required_keys(self):
        required = ["north", "south", "east", "west",
                    "trips_filename", "subdistricts_filename", "sample_size"]
        for k in required:
            self.assertIn(k, self.cfg["input"], f"Missing key: {k}")

    def test_execution_section_has_required_keys(self):
        required = ["run_simulation_automatically", "maven_opts",
                    "matsim_config_file", "apply_traffic_conditions",
                    "traffic_conditions_file"]
        for k in required:
            self.assertIn(k, self.cfg["execution"], f"Missing key: {k}")

    def test_bbox_values_are_numeric(self):
        inp = self.cfg["input"]
        for k in ["north", "south", "east", "west"]:
            self.assertIsInstance(inp[k], (int, float), f"{k} should be numeric")

    def test_bbox_north_greater_than_south(self):
        self.assertGreater(self.cfg["input"]["north"], self.cfg["input"]["south"])

    def test_bbox_east_greater_than_west(self):
        self.assertGreater(self.cfg["input"]["east"], self.cfg["input"]["west"])

    def test_bbox_is_in_bangkok_range(self):
        inp = self.cfg["input"]
        self.assertGreater(inp["north"], 13.5)
        self.assertLess(inp["south"],    14.0)
        self.assertGreater(inp["east"],  100.3)
        self.assertLess(inp["west"],     100.7)

    def test_sample_size_is_positive_int(self):
        ss = self.cfg["input"]["sample_size"]
        self.assertIsInstance(ss, int)
        self.assertGreater(ss, 0)

    def test_save_and_reload_preserves_all_sections(self):
        tmp = tempfile.mkdtemp()
        tmp_cfg = os.path.join(tmp, "config.json")
        orig = gui.CONFIG_PATH
        try:
            gui.CONFIG_PATH = tmp_cfg
            gui.save_config(self.cfg)
            reloaded = gui.load_config()
            self.assertEqual(reloaded["input"]["sample_size"],
                             self.cfg["input"]["sample_size"])
            self.assertEqual(reloaded["execution"]["maven_opts"],
                             self.cfg["execution"]["maven_opts"])
        finally:
            gui.CONFIG_PATH = orig
            shutil.rmtree(tmp)

    def test_smart_path_on_real_trips_filename(self):
        trips = self.cfg["input"]["trips_filename"]
        # Should not crash — just verify it returns a string
        full = os.path.join(ROOT, trips)
        result = gui._smart_path(full)
        self.assertIsInstance(result, str)


# ══════════════════════════════════════════════════════════════════════════════
# 2B. apply_traffic_conditions integration
#     Real network + real traffic_conditions.json → output network
# ══════════════════════════════════════════════════════════════════════════════

class TestApplyTrafficConditionsIntegration(unittest.TestCase):

    NETWORK_IN  = os.path.join(ROOT, "data", "processed", "network.xml.gz")
    TC_FILE     = os.path.join(ROOT, "data", "traffic_conditions.json")

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out_network = os.path.join(self.tmp, "network_test.xml.gz")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    @unittest.skipUnless(
        os.path.exists(os.path.join(ROOT, "data", "processed", "network.xml.gz")),
        "network.xml.gz not available")
    def test_load_conditions_returns_three_tuple(self):
        result = load_conditions(self.TC_FILE, project_root=ROOT)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)

    @unittest.skipUnless(
        os.path.exists(os.path.join(ROOT, "data", "processed", "network.xml.gz")),
        "network.xml.gz not available")
    def test_apply_conditions_creates_output_file(self):
        result = load_conditions(self.TC_FILE, project_root=ROOT)
        self.assertIsNotNone(result)
        _, _, conds = result
        apply_conditions(self.NETWORK_IN, self.out_network, conds)
        self.assertTrue(os.path.exists(self.out_network),
                        "Output network file was not created")

    @unittest.skipUnless(
        os.path.exists(os.path.join(ROOT, "data", "processed", "network.xml.gz")),
        "network.xml.gz not available")
    def test_output_is_valid_gzip(self):
        result = load_conditions(self.TC_FILE, project_root=ROOT)
        _, _, conds = result
        apply_conditions(self.NETWORK_IN, self.out_network, conds)
        try:
            with gzip.open(self.out_network, "rb") as f:
                chunk = f.read(1024)
            self.assertGreater(len(chunk), 0)
        except Exception as e:
            self.fail(f"Output gzip is invalid: {e}")

    @unittest.skipUnless(
        os.path.exists(os.path.join(ROOT, "data", "processed", "network.xml.gz")),
        "network.xml.gz not available")
    def test_closed_links_removed_from_output(self):
        """Links with capacity_factor=0 must not appear in output network."""
        import re
        result = load_conditions(self.TC_FILE, project_root=ROOT)
        _, _, conds = result
        apply_conditions(self.NETWORK_IN, self.out_network, conds)

        # find all link_ids with capacity_factor=0
        closed_ids = {str(c["link_id"]) for c in conds
                      if "link_id" in c and c.get("capacity_factor", 1) == 0}

        if not closed_ids:
            self.skipTest("No closed links in traffic_conditions.json")

        with gzip.open(self.out_network, "rt", encoding="utf-8") as f:
            content = f.read()
        for lid in closed_ids:
            self.assertNotIn(f'id="{lid}"', content,
                             f"Closed link {lid} should be removed from network")

    @unittest.skipUnless(
        os.path.exists(os.path.join(ROOT, "data", "processed", "network.xml.gz")),
        "network.xml.gz not available")
    def test_rain_condition_reduces_freespeed(self):
        """Heavy rain condition must lower freespeed of road-type links."""
        import re
        from lxml import etree

        result = load_conditions(self.TC_FILE, project_root=ROOT)
        _, _, conds = result

        # Get speed factor for rain condition
        rain = next((c for c in conds if "road_types" in c), None)
        if rain is None:
            self.skipTest("No road_types condition found")

        apply_conditions(self.NETWORK_IN, self.out_network, conds)

        # Spot-check: parse first 50 links and verify freespeed < original
        with gzip.open(self.NETWORK_IN, "rb") as f:
            orig_tree = etree.parse(f)
        with gzip.open(self.out_network, "rb") as f:
            cond_tree = etree.parse(f)

        orig_links = {l.get("id"): float(l.get("freespeed", 0))
                      for l in orig_tree.getroot().find("links").findall("link")[:50]}
        cond_links = {l.get("id"): float(l.get("freespeed", 0))
                      for l in cond_tree.getroot().find("links").findall("link")[:50]}

        slower = sum(1 for lid, fs in cond_links.items()
                     if lid in orig_links and fs < orig_links[lid])
        self.assertGreater(slower, 0, "No links were slowed down by rain condition")


# ══════════════════════════════════════════════════════════════════════════════
# 2C. pipeline/data files integration
#     Real final_trips.csv + subdistricts_180.geojson are readable and consistent
# ══════════════════════════════════════════════════════════════════════════════

class TestPipelineDataIntegration(unittest.TestCase):

    TRIPS_CSV = os.path.join(ROOT, "pipeline", "data", "final_trips.csv")
    GEOJSON   = os.path.join(ROOT, "pipeline", "data", "subdistricts_180.geojson")

    @unittest.skipUnless(
        os.path.exists(os.path.join(ROOT, "pipeline", "data", "final_trips.csv")),
        "final_trips.csv not available")
    def test_trips_csv_loads(self):
        import pandas as pd
        df = pd.read_csv(self.TRIPS_CSV, low_memory=False)
        self.assertGreater(len(df), 0)

    @unittest.skipUnless(
        os.path.exists(os.path.join(ROOT, "pipeline", "data", "final_trips.csv")),
        "final_trips.csv not available")
    def test_trips_has_required_columns(self):
        import pandas as pd
        df = pd.read_csv(self.TRIPS_CSV, low_memory=False, nrows=5)
        for col in ["person_id", "origin"]:
            self.assertIn(col, df.columns, f"Missing column: {col}")

    @unittest.skipUnless(
        os.path.exists(os.path.join(ROOT, "pipeline", "data", "subdistricts_180.geojson")),
        "subdistricts_180.geojson not available")
    def test_geojson_loads(self):
        import geopandas as gpd
        gdf = gpd.read_file(self.GEOJSON)
        self.assertGreater(len(gdf), 0)

    @unittest.skipUnless(
        os.path.exists(os.path.join(ROOT, "pipeline", "data", "subdistricts_180.geojson")),
        "subdistricts_180.geojson not available")
    def test_geojson_has_objectid(self):
        import geopandas as gpd
        gdf = gpd.read_file(self.GEOJSON)
        self.assertIn("OBJECTID", gdf.columns)

    @unittest.skipUnless(
        os.path.exists(os.path.join(ROOT, "pipeline", "data", "subdistricts_180.geojson")),
        "subdistricts_180.geojson not available")
    def test_geojson_covers_bangkok_area(self):
        import geopandas as gpd
        gdf = gpd.read_file(self.GEOJSON).to_crs("EPSG:4326")
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        self.assertGreater(bounds[2], 100.3, "East bound too low for Bangkok")
        self.assertLess(bounds[0],    100.7, "West bound too high for Bangkok")

    @unittest.skipUnless(
        os.path.exists(os.path.join(ROOT, "pipeline", "data", "final_trips.csv")) and
        os.path.exists(os.path.join(ROOT, "pipeline", "data", "subdistricts_180.geojson")),
        "Required data files not available")
    def test_origin_taz_ids_exist_in_geojson(self):
        """All TAZ origin IDs in trips CSV must exist in the GeoJSON."""
        import pandas as pd
        import geopandas as gpd
        df  = pd.read_csv(self.TRIPS_CSV, usecols=["origin"], low_memory=False)
        gdf = gpd.read_file(self.GEOJSON)
        trip_tazs   = set(df["origin"].dropna().unique())
        geojson_ids = set(gdf["OBJECTID"].astype(int).unique())
        missing = trip_tazs - geojson_ids
        self.assertEqual(len(missing), 0,
                         f"{len(missing)} TAZ IDs in trips not found in GeoJSON: {list(missing)[:5]}")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [TestConfigGuiIntegration,
                TestApplyTrafficConditionsIntegration,
                TestPipelineDataIntegration]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    print("=" * 60)
    print("  INTEGRATION TESTS")
    print("=" * 60)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total  = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"\n  PASSED {passed}/{total}")
    sys.exit(0 if result.wasSuccessful() else 1)
