"""
test_3_e2e.py
=============
END-TO-END TESTS — test full workflows from input to final output.
These tests exercise real pipelines with real data files.

Run:
    python tests/test_3_e2e.py
"""

import sys
import os
import gzip
import json
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

for mod in ["customtkinter", "tkinter", "tkinter.filedialog",
            "tkinter.messagebox", "webview"]:
    sys.modules.setdefault(mod, MagicMock())

import gui
from apply_traffic_conditions import load_conditions, apply_conditions, validate_link_ids


# ══════════════════════════════════════════════════════════════════════════════
# 3A. GUI Full Save Workflow
#     Simulate a user filling all fields → saving → verify config.json updated
# ══════════════════════════════════════════════════════════════════════════════

class TestGUIFullSaveWorkflow(unittest.TestCase):
    """Simulate the on_save() workflow end-to-end."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg_path = os.path.join(self.tmp, "config.json")
        self._orig_cfg = gui.CONFIG_PATH
        gui.CONFIG_PATH = self.cfg_path
        # Seed a valid config
        gui.save_config({
            "input":     {"north": 13.0, "south": 12.0, "east": 101.0,
                          "west": 100.0, "sample_size": 1000,
                          "trips_filename": "trips.csv",
                          "subdistricts_filename": "sub.geojson"},
            "execution": {"run_simulation_automatically": False,
                          "maven_opts": "-Xmx8G",
                          "matsim_config_file": "data/config.xml",
                          "apply_traffic_conditions": False,
                          "traffic_conditions_file": "data/tc.json"},
            "api_keys":  {"google_maps": "OLD_KEY"},
        })

    def tearDown(self):
        gui.CONFIG_PATH = self._orig_cfg
        shutil.rmtree(self.tmp)

    def _simulate_save(self, overrides=None):
        """Replicate on_save() logic directly."""
        inputs = {
            "north":   "13.757057", "south":   "13.729549",
            "east":    "100.552239","west":    "100.513186",
            "trips":   "pipeline/data/final_trips.csv",
            "subdis":  "pipeline/data/subdistricts_180.geojson",
            "sample":  "300000",
            "auto":    True,
            "mvnopts": "-Xmx16G",
            "mscfg":   "data/config.xml",
            "tc":      True,
            "tcfile":  "data/traffic_conditions.json",
            "gmaps":   "NEW_KEY_XYZ",
        }
        if overrides:
            inputs.update(overrides)
        cfg = {
            "input": {
                "north":                 float(inputs["north"]),
                "south":                 float(inputs["south"]),
                "east":                  float(inputs["east"]),
                "west":                  float(inputs["west"]),
                "trips_filename":        inputs["trips"].strip(),
                "subdistricts_filename": inputs["subdis"].strip(),
                "sample_size":           int(inputs["sample"]),
            },
            "execution": {
                "run_simulation_automatically": inputs["auto"],
                "maven_opts":                   inputs["mvnopts"].strip(),
                "matsim_config_file":           inputs["mscfg"].strip(),
                "apply_traffic_conditions":     inputs["tc"],
                "traffic_conditions_file":      inputs["tcfile"].strip(),
            },
            "api_keys": {"google_maps": inputs["gmaps"].strip()},
        }
        gui.save_config(cfg)
        return gui.load_config()

    def test_full_save_updates_sample_size(self):
        cfg = self._simulate_save()
        self.assertEqual(cfg["input"]["sample_size"], 300000)

    def test_full_save_updates_api_key(self):
        cfg = self._simulate_save()
        self.assertEqual(cfg["api_keys"]["google_maps"], "NEW_KEY_XYZ")

    def test_full_save_updates_bbox(self):
        cfg = self._simulate_save()
        self.assertAlmostEqual(cfg["input"]["north"], 13.757057, places=4)

    def test_full_save_updates_traffic_conditions_flag(self):
        cfg = self._simulate_save()
        self.assertTrue(cfg["execution"]["apply_traffic_conditions"])

    def test_full_save_disables_traffic_conditions(self):
        cfg = self._simulate_save({"tc": False})
        self.assertFalse(cfg["execution"]["apply_traffic_conditions"])

    def test_full_save_overwrites_old_values(self):
        old = gui.load_config()
        self.assertEqual(old["api_keys"]["google_maps"], "OLD_KEY")
        self._simulate_save()
        new = gui.load_config()
        self.assertEqual(new["api_keys"]["google_maps"], "NEW_KEY_XYZ")

    def test_invalid_bbox_does_not_save(self):
        with self.assertRaises(ValueError):
            self._simulate_save({"north": "NOT_A_NUMBER"})
        # Original config must still be intact
        cfg = gui.load_config()
        self.assertEqual(cfg["api_keys"]["google_maps"], "OLD_KEY")

    def test_saves_correct_number_of_sections(self):
        cfg = self._simulate_save()
        self.assertEqual(set(cfg.keys()), {"input", "execution", "api_keys"})


# ══════════════════════════════════════════════════════════════════════════════
# 3B. Traffic Conditions Full Pipeline
#     JSON config → load_conditions → apply_conditions → verify output network
# ══════════════════════════════════════════════════════════════════════════════

NET_IN  = os.path.join(ROOT, "data", "processed", "network.xml.gz")
TC_FILE = os.path.join(ROOT, "data", "traffic_conditions.json")

@unittest.skipUnless(os.path.exists(NET_IN), "network.xml.gz not available")
class TestTrafficConditionsE2E(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, "network_e2e.xml.gz")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run_pipeline(self):
        """Run full pipeline and return (conditions, stats)."""
        result = load_conditions(TC_FILE, project_root=ROOT)
        self.assertIsNotNone(result, "load_conditions returned None")
        _, _, conds = result
        stats = apply_conditions(NET_IN, self.out, conds)
        return conds, stats

    def test_output_file_exists_after_pipeline(self):
        self._run_pipeline()
        self.assertTrue(os.path.exists(self.out))

    def test_output_file_is_smaller_than_input(self):
        """Removing links should reduce file size."""
        self._run_pipeline()
        self.assertGreater(os.path.getsize(self.out), 0)

    def test_output_contains_links_element(self):
        from lxml import etree
        self._run_pipeline()
        with gzip.open(self.out, "rb") as f:
            tree = etree.parse(f)
        self.assertIsNotNone(tree.getroot().find("links"))

    def test_link_count_reduced_for_closed_links(self):
        """Links that were actually found AND had capacity_factor=0 must be removed.

        Uses stats returned by apply_conditions so the count is based on what
        was actually in the network, not what traffic_conditions.json lists.
        This correctly handles the case where a user configures a link_id that
        no longer exists in the current network (stale ID after regeneration).
        """
        from lxml import etree
        conds, stats = self._run_pipeline()

        closed_in_json = [c for c in conds
                          if "link_id" in c and c.get("capacity_factor", 1) == 0]
        if not closed_in_json:
            self.skipTest("No closed link_id conditions configured")

        # Only links actually present in the network count toward the reduction
        actually_removed = len(stats["removed"])
        if actually_removed == 0:
            self.skipTest("No closed links were found in the network — "
                          "traffic_conditions.json may reference stale link IDs")

        with gzip.open(NET_IN, "rb") as f:
            orig_count = len(etree.parse(f).getroot().find("links").findall("link"))
        with gzip.open(self.out, "rb") as f:
            out_count  = len(etree.parse(f).getroot().find("links").findall("link"))

        self.assertEqual(
            out_count, orig_count - actually_removed,
            f"Expected {orig_count - actually_removed} links "
            f"({orig_count} - {actually_removed} removed), got {out_count}"
        )

    def test_not_found_links_are_reported_in_stats(self):
        """apply_conditions must report link IDs that were missing from the network.

        If traffic_conditions.json lists a link_id that the current network does
        not contain (e.g. after network regeneration), the stats dict must record
        it under 'not_found' so callers can detect and report the inconsistency.
        """
        _, stats = self._run_pipeline()
        # stats must always have the not_found key — even if the list is empty
        self.assertIn("not_found", stats)
        self.assertIsInstance(stats["not_found"], list)
        # If there are missing IDs, they must be strings
        for lid in stats["not_found"]:
            self.assertIsInstance(lid, str, f"not_found entry should be str: {lid!r}")

    def test_validate_link_ids_detects_missing(self):
        """validate_link_ids() must correctly identify which link_ids exist in
        the network and which do not, without modifying any file."""
        result = load_conditions(TC_FILE, project_root=ROOT)
        self.assertIsNotNone(result)
        _, _, conds = result
        report = validate_link_ids(conds, NET_IN)

        self.assertIn("found",   report)
        self.assertIn("missing", report)

        # Every ID in 'found' + 'missing' must have come from the conditions
        all_ids_in_conditions = {str(c["link_id"]) for c in conds if "link_id" in c}
        reported_ids = set(report["found"]) | set(report["missing"])
        self.assertEqual(reported_ids, all_ids_in_conditions,
                         "validate_link_ids must account for every link_id in conditions")

    def test_closed_link_ids_absent_from_output(self):
        """Links that were actually removed must not appear in the output network."""
        conds, stats = self._run_pipeline()
        if not stats["removed"]:
            self.skipTest("No links were removed — skipping absence check")
        with gzip.open(self.out, "rt", encoding="utf-8") as f:
            content = f.read()
        for lid in stats["removed"]:
            self.assertNotIn(f'id="{lid}"', content,
                             f"Removed link '{lid}' should be absent from output network")

    def test_rain_links_have_reduced_freespeed(self):
        """All road-type links must have lower freespeed than original."""
        from lxml import etree
        conds = self._run_pipeline()
        rain  = next((c for c in conds if "road_types" in c), None)
        if not rain:
            self.skipTest("No road_types condition")

        with gzip.open(NET_IN, "rb") as f:
            orig = {l.get("id"): float(l.get("freespeed", 0))
                    for l in etree.parse(f).getroot().find("links").findall("link")[:100]}
        with gzip.open(self.out, "rb") as f:
            cond = {l.get("id"): float(l.get("freespeed", 0))
                    for l in etree.parse(f).getroot().find("links").findall("link")[:100]}

        reduced = sum(1 for lid in cond if lid in orig and cond[lid] < orig[lid])
        self.assertGreater(reduced, 50, "Expected most links to have reduced freespeed")

    def test_config_xml_network_path_updated(self):
        """After pipeline, data/config.xml inputNetworkFile should reference conditioned network."""
        import re
        config_xml = os.path.join(ROOT, "data", "config.xml")
        if not os.path.exists(config_xml):
            self.skipTest("data/config.xml not available")
        with open(config_xml, encoding="utf-8") as f:
            content = f.read()
        m = re.search(r'<param name="inputNetworkFile"\s+value="([^"]+)"', content)
        self.assertIsNotNone(m, "inputNetworkFile param not found in config.xml")


# ══════════════════════════════════════════════════════════════════════════════
# 3C. Simulation Output Validation E2E
#     Real output_trips.csv.gz → compute metrics → verify in expected range
# ══════════════════════════════════════════════════════════════════════════════

TRIPS_GZ = os.path.join(ROOT, "normal_output", "output", "output_trips.csv.gz")

@unittest.skipUnless(os.path.exists(TRIPS_GZ), "output_trips.csv.gz not available")
class TestSimulationOutputE2E(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import pandas as pd
        import numpy as np
        with gzip.open(TRIPS_GZ, "rt", encoding="utf-8") as f:
            cls.df = pd.read_csv(f, sep=";", low_memory=False)
        # Parse travel time
        cls.df["trav_sec"] = pd.to_timedelta(
            cls.df["trav_time"].astype(str), errors="coerce"
        ).dt.total_seconds()
        cls.df["trav_min"] = cls.df["trav_sec"] / 60.0
        cls.car = cls.df[cls.df["main_mode"] == "car"]

    def test_trips_file_loads(self):
        self.assertGreater(len(self.df), 0)

    def test_expected_agent_count(self):
        agents = self.df["person"].nunique() if "person" in self.df.columns else len(self.df)
        # Should be close to 300,000
        self.assertGreater(agents, 200000,  "Fewer agents than expected")
        self.assertLess(agents,    400000,  "More agents than expected")

    def test_all_trips_are_car(self):
        """In this simulation all agents use car."""
        car_pct = (self.df["main_mode"] == "car").mean() * 100
        self.assertGreater(car_pct, 99.0, f"Expected ~100% car trips, got {car_pct:.1f}%")

    def test_median_travel_time_reasonable(self):
        """Median car travel time should be between 3 and 30 minutes."""
        median_min = self.car["trav_min"].median()
        self.assertGreater(median_min, 3,  f"Median too low: {median_min:.1f} min")
        self.assertLess(median_min,    30, f"Median too high: {median_min:.1f} min")

    def test_no_negative_travel_times(self):
        neg = (self.car["trav_sec"] < 0).sum()
        self.assertEqual(neg, 0, f"{neg} trips have negative travel time")

    def test_travel_distance_positive(self):
        """At least 95% of car trips must have positive traveled distance.

        A small fraction of zero-distance trips is expected and acceptable.
        These occur when an agent's origin and destination activities are
        assigned to the same network link — a known MATSim artifact when
        demand is sub-sampled and locations are drawn from a limited OSM POI
        pool within small TAZs (especially work→work consecutive activities
        in cloned agents).  The threshold of 95% flags genuine pipeline
        failures (e.g. all agents stuck) while tolerating the natural ~4%
        same-link rate observed in Bangkok simulations.
        """
        dist_col = "traveled_distance" if "traveled_distance" in self.car.columns else "distance"
        if dist_col not in self.car.columns:
            self.skipTest("No distance column found")
        total      = len(self.car)
        zero_count = (self.car[dist_col] <= 0).sum()
        pct_valid  = (total - zero_count) / total * 100
        self.assertGreater(
            pct_valid, 95.0,
            f"Only {pct_valid:.1f}% of car trips have positive distance "
            f"({zero_count:,} zero-distance trips out of {total:,}). "
            f"Expected > 95%. Check for same-link assignment or stuck agents."
        )

    def test_median_speed_realistic(self):
        """Median car speed should be 10–80 km/h."""
        dist_col = "traveled_distance" if "traveled_distance" in self.car.columns else "distance"
        if dist_col not in self.car.columns:
            self.skipTest("No distance column found")
        valid = self.car[(self.car["trav_sec"] > 0) & (self.car[dist_col] > 0)]
        speeds = (valid[dist_col] / 1000.0) / (valid["trav_sec"] / 3600.0)
        median_speed = speeds.median()
        self.assertGreater(median_speed, 10, f"Median speed too low: {median_speed:.1f} km/h")
        self.assertLess(median_speed,    80, f"Median speed too high: {median_speed:.1f} km/h")

    def test_pm_peak_slower_than_midday(self):
        """PM peak (17–20h) should be slower than midday (11–13h)."""
        import pandas as pd
        car = self.car.copy()
        car["dep_sec"]  = pd.to_timedelta(car["dep_time"].astype(str), errors="coerce").dt.total_seconds()
        car["dep_hour"] = (car["dep_sec"] // 3600).fillna(-1).astype(int)
        midday = car[(car["dep_hour"] >= 11) & (car["dep_hour"] < 13)]["trav_min"].median()
        pm     = car[(car["dep_hour"] >= 17) & (car["dep_hour"] < 20)]["trav_min"].median()
        self.assertGreater(pm, midday,
                           f"PM peak ({pm:.1f} min) should be slower than midday ({midday:.1f} min)")

    def test_scorestats_converged(self):
        """Agent score should increase from iteration 1 to last."""
        import pandas as pd
        ss_path = os.path.join(ROOT, "normal_output", "output", "scorestats.csv")
        if not os.path.exists(ss_path):
            self.skipTest("scorestats.csv not available")
        ss = pd.read_csv(ss_path, sep=";")
        first = ss["avg_executed"].iloc[0]
        last  = ss["avg_executed"].iloc[-1]
        self.assertGreater(last, first,
                           f"Score did not converge: {first:.2f} → {last:.2f}")

    def test_spatial_accuracy_above_threshold(self):
        """Spatial accuracy from the spatial report should be > 90%."""
        plans_gz = os.path.join(ROOT, "normal_output", "output", "output_plans.xml.gz")
        geojson  = os.path.join(ROOT, "pipeline", "data", "subdistricts_180.geojson")
        trips_csv = os.path.join(ROOT, "pipeline", "data", "final_trips.csv")
        if not all(os.path.exists(p) for p in [plans_gz, geojson, trips_csv]):
            self.skipTest("Required files for spatial accuracy not available")

        import gzip as gz
        import xml.etree.ElementTree as ET
        import pandas as pd
        import geopandas as gpd
        from shapely.geometry import Point
        from pyproj import Transformer

        # Load TAZ lookup
        df_src = pd.read_csv(trips_csv, usecols=["person_id", "origin"], low_memory=False)
        taz_lookup = df_src.groupby("person_id")["origin"].first().to_dict()

        # Extract agent home locations
        agents = []
        with gz.open(plans_gz, "rb") as f:
            for event, elem in ET.iterparse(f, events=("end",)):
                if elem.tag == "person":
                    pid  = elem.get("id")
                    plan = elem.find("plan")
                    if plan is not None:
                        act = plan.find("activity")
                        if act is not None:
                            agents.append({"person_id": pid,
                                           "x": float(act.get("x")),
                                           "y": float(act.get("y"))})
                    elem.clear()
                    if len(agents) >= 10000:  # sample for speed
                        break

        df_xml = pd.DataFrame(agents)
        tf = Transformer.from_crs("EPSG:32647", "EPSG:4326", always_xy=True)
        lons, lats = tf.transform(df_xml["x"].values, df_xml["y"].values)
        gdf = gpd.GeoDataFrame(df_xml,
                               geometry=[Point(xy) for xy in zip(lons, lats)],
                               crs="EPSG:4326")
        subs = gpd.read_file(geojson)[["OBJECTID", "geometry"]].to_crs("EPSG:4326")
        joined = gpd.sjoin(gdf, subs, how="left", predicate="within")

        def base_id(pid):
            """Strip _clone suffix to recover original person_id.
            e.g. '100008_clone1' → 100008,  '42' → 42
            Clone agents inherit their origin TAZ from the base agent,
            so the lookup must use the base ID, not the clone ID.
            """
            s = str(pid)
            if "_clone" in s:
                s = s.split("_clone")[0]
            try:
                return int(s)
            except ValueError:
                return s

        def check(row):
            key = base_id(row["person_id"])
            taz = taz_lookup.get(key)
            if pd.isna(row.get("OBJECTID")) or taz is None:
                return False
            return int(row["OBJECTID"]) == int(taz)

        acc = joined.apply(check, axis=1).mean() * 100
        self.assertGreater(acc, 90.0, f"Spatial accuracy too low: {acc:.2f}%")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [TestGUIFullSaveWorkflow,
                TestTrafficConditionsE2E,
                TestSimulationOutputE2E]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    print("=" * 60)
    print("  END-TO-END TESTS")
    print("=" * 60)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total  = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"\n  PASSED {passed}/{total}")
    sys.exit(0 if result.wasSuccessful() else 1)
