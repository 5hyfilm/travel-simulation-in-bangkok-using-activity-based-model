import os
import time
import json
import subprocess
import platform
from get_osm_network import download_osm_for_matsim
from get_facilities import extract_poi_to_csv
from process_facilities import classify_facilities
from assign_locations import assign_facility_locations
from generate_plans import generate_matsim_plans
from clean_plans import process_file as fix_plan_home_end
from apply_traffic_conditions import load_conditions, apply_conditions

# Fixed output directory — all pipeline outputs live here
PIPELINE_DIR = os.path.dirname(__file__)
OUT_DIR      = os.path.join(PIPELINE_DIR, "output")

def main():
    print("=== Starting MATSim data preparation process ===")

    # Load configuration from JSON
    config_path = os.path.abspath(os.path.join(PIPELINE_DIR, "..", "config.json"))
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found!")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    input_config = config["input"]
    project_root = os.path.abspath(os.path.join(PIPELINE_DIR, ".."))

    def resolve(path):
        """Resolve a path against the project root if it is not absolute."""
        if os.path.isabs(path):
            return path
        return os.path.join(project_root, path)

    # All output paths are fixed inside pipeline/output/
    os.makedirs(OUT_DIR, exist_ok=True)
    osm_path         = os.path.join(OUT_DIR, "network.osm")
    raw_csv_path     = os.path.join(OUT_DIR, "facilities_raw.csv")
    clean_csv_path   = os.path.join(OUT_DIR, "facilities_cleaned.csv")
    trips_path       = resolve(input_config["trips_filename"])
    final_trips_path = os.path.join(OUT_DIR, "final_trips.csv")
    plans_path       = os.path.join(OUT_DIR, "plan_raw.xml")
    cut_output_path  = os.path.join(OUT_DIR, "plan.xml")

    start_time = time.time()

    # Step 1: Download Map
    print(f"\n[Step 1] Downloading map network to: {osm_path}")
    download_osm_for_matsim(
        input_config["north"], input_config["south"],
        input_config["east"],  input_config["west"],
        osm_path
    )

    # Step 2: Extract Raw Facilities
    print(f"\n[Step 2] Extracting raw facilities data to: {raw_csv_path}")
    extract_poi_to_csv(
        input_config["north"], input_config["south"],
        input_config["east"],  input_config["west"],
        raw_csv_path,
        osm_file_path=osm_path
    )

    # Step 3: Classify Facilities + assign TAZ ID
    print(f"\n[Step 3] Classifying activities and saving to: {clean_csv_path}")
    classify_facilities(raw_csv_path, clean_csv_path,
                        subdistricts_path=resolve(input_config["subdistricts_filename"]))

    # Step 4: Assign Locations
    print(f"\n[Step 4] Assigning locations to trips: {final_trips_path}")
    if os.path.exists(trips_path):
        assign_facility_locations(trips_path, clean_csv_path, final_trips_path,
                                  target_size=input_config["sample_size"])
    else:
        print(f"[Note] {trips_path} not found. Skipping Step 4 & 5.")
        print(f"Please provide the trips CSV and set trips_filename in config.json.")
        end_time = time.time()
        print(f"\n=== Completed partially! Total time: {end_time - start_time:.2f} seconds ===")
        return

    # Step 5: Generate MATSim Plans
    print(f"\n[Step 5] Generating MATSim XML plans: {plans_path}")
    generate_matsim_plans(
        final_trips_path,
        plans_path,
        sample_size=input_config["sample_size"],
        bbox=(input_config["north"], input_config["south"],
              input_config["east"],  input_config["west"])
    )

    # Step 5b: Cut / fix agents (trims plans that don't end with home)
    print(f"\n[Step 5b] Cutting & fixing agent plans: {cut_output_path}")
    fix_plan_home_end(plans_path, cut_output_path, dry_run=False)

    end_time = time.time()
    print(f"\n=== Preprocessing Completed! Total time: {end_time - start_time:.2f} seconds ===")
    print(f"Final plan: {cut_output_path}")

    # ==========================================
    # AUTO-EXECUTION MODULE (MATSim)
    # ==========================================
    exec_config = config.get("execution", {})

    if exec_config.get("run_simulation_automatically", False):
        print("\n=== Starting Automatic MATSim Execution ===")

        maven_opts    = exec_config.get("maven_opts", "-Xmx10G")
        matsim_config = exec_config.get("matsim_config_file", "data/config.xml")
        if not os.path.isabs(matsim_config):
            matsim_config = os.path.join(project_root, matsim_config)

        env = os.environ.copy()
        env["MAVEN_OPTS"] = maven_opts

        maven_cmd = os.path.join(project_root, "mvnw.cmd" if platform.system() == "Windows" else "mvnw")
        if not os.path.exists(maven_cmd):
            print(f"[ERROR] Maven Wrapper not found: {maven_cmd}")
            return

        # Step 6: Convert OSM → MATSim network (compile forces rebuild of changed sources)
        print("\n[Step 6] Converting OSM to MATSim Network...")
        subprocess.run([
            maven_cmd, "compile", "exec:java",
            "-Dexec.mainClass=org.matsim.project.ConvertOSM",
        ], cwd=project_root, env=env, check=True)

        # Step 6b: Apply traffic conditions AFTER network is built (optional)
        apply_tc = exec_config.get("apply_traffic_conditions", False)
        if apply_tc:
            conditions_file = exec_config.get("traffic_conditions_file", "data/traffic_conditions.json")
            if not os.path.isabs(conditions_file):
                conditions_file = os.path.join(project_root, conditions_file)
            print(f"\n[Step 6b] Applying traffic conditions from: {conditions_file}")
            result = load_conditions(conditions_file, project_root=project_root)
            if result is not None:
                input_network, output_network, conds = result
                apply_conditions(input_network, output_network, conds)
                active_network = "processed/network_condition.xml.gz"
            else:
                print("[Step 6b] Skipped — could not load traffic conditions.")
                active_network = "processed/network.xml.gz"
        else:
            print("\n[Step 6b] Traffic conditions: disabled — using baseline network.")
            active_network = "processed/network.xml.gz"

        # Update data/config.xml with network file, iteration count, and capacity factors
        matsim_config_path = os.path.join(project_root, "data", "config.xml")
        with open(matsim_config_path, encoding="utf-8") as f:
            cfg_xml = f.read()
        import re

        # Network file
        cfg_xml = re.sub(
            r'(<param name="inputNetworkFile"\s+value=")[^"]*(")',
            rf'\g<1>{active_network}\g<2>',
            cfg_xml
        )

        # Iteration count and derived write/reroute intervals
        iterations      = exec_config.get("iterations", 0)
        write_interval  = max(1, iterations)          # write at final iteration (min 1)
        disable_reroute = int(iterations * 0.8)       # stop rerouting at 80% of iterations

        cfg_xml = re.sub(
            r'(<param name="lastIteration"\s+value=")[^"]*(")',
            rf'\g<1>{iterations}\g<2>',
            cfg_xml
        )
        cfg_xml = re.sub(
            r'(<param name="writeEventsInterval"\s+value=")[^"]*(")',
            rf'\g<1>{write_interval}\g<2>',
            cfg_xml
        )
        cfg_xml = re.sub(
            r'(<param name="writePlansInterval"\s+value=")[^"]*(")',
            rf'\g<1>{write_interval}\g<2>',
            cfg_xml
        )
        cfg_xml = re.sub(
            r'(<param name="disableAfterIteration"\s+value=")[^"]*(")',
            rf'\g<1>{disable_reroute}\g<2>',
            cfg_xml
        )

        # Capacity factors — scale down road capacity proportionally to sample size
        # flowCapacityFactor = storageCapacityFactor = sample_size / population_size
        real_pop    = input_config.get("population_size", 10000000)
        sample_size = input_config.get("sample_size", real_pop)
        cap_factor  = round(sample_size / real_pop, 6) if real_pop > 0 else 1.0
        cfg_xml = re.sub(
            r'(<param name="flowCapacityFactor"\s+value=")[^"]*(")',
            rf'\g<1>{cap_factor}\g<2>',
            cfg_xml
        )
        cfg_xml = re.sub(
            r'(<param name="storageCapacityFactor"\s+value=")[^"]*(")',
            rf'\g<1>{cap_factor}\g<2>',
            cfg_xml
        )

        with open(matsim_config_path, "w", encoding="utf-8") as f:
            f.write(cfg_xml)
        print(f"\n[Config] inputNetworkFile        → {active_network}")
        print(f"[Config] lastIteration           → {iterations}")
        print(f"[Config] writeEventsInterval     → {write_interval}")
        print(f"[Config] writePlansInterval      → {write_interval}")
        print(f"[Config] disableAfterIteration   → {disable_reroute}  (80% of {iterations})")
        print(f"[Config] flowCapacityFactor      → {cap_factor}  ({sample_size:,} / {real_pop:,})")
        print(f"[Config] storageCapacityFactor   → {cap_factor}")

        # Step 7: Run MATSim
        print(f"\n[Step 7] Running MATSim with config: {matsim_config}...")
        subprocess.run([
            maven_cmd, "exec:java",
            "-Dexec.mainClass=org.matsim.project.RunMatsim",
            f"-Dexec.args={matsim_config}",
        ], cwd=project_root, env=env, check=True)

        print("\n=== All processes completed successfully! ===")
    else:
        if exec_config.get("apply_traffic_conditions", False):
            print("\n[Note] Traffic conditions are enabled but will only apply when")
            print("       'Run Simulation Automatically' is turned on (after ConvertOSM runs).")
        else:
            print("\n[Note] Traffic conditions: disabled.")

if __name__ == "__main__":
    main()
