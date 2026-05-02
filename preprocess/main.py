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
from fix_plan_home_end import process_file as fix_plan_home_end
from apply_traffic_conditions import load_conditions, apply_conditions

def main():
    print("=== Starting MATSim data preparation process ===")

    # Load configuration from JSON
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.json"))
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found!")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    input_config = config["input"]
    output_config = config["output"]

    if not os.path.exists(output_config["output_folder"]):
        os.makedirs(output_config["output_folder"], exist_ok=True)

    osm_path        = os.path.join(output_config["output_folder"], output_config["osm_filename"])
    raw_csv_path    = os.path.join(output_config["output_folder"], output_config["raw_csv_filename"])
    clean_csv_path  = os.path.join(output_config["output_folder"], output_config["clean_csv_filename"])
    trips_path      = input_config["trips_filename"]
    final_trips_path = os.path.join(output_config["output_folder"], output_config["final_trips_filename"])
    plans_path      = os.path.join(output_config["output_folder"], output_config["plans_filename"])

    start_time = time.time()

    # Step 1: Download Map
    print(f"\n[Step 1/5] Downloading map network to: {osm_path}")
    download_osm_for_matsim(
        input_config["north"], input_config["south"], input_config["east"], input_config["west"],
        osm_path
    )

    # Step 2: Extract Raw Facilities
    print(f"\n[Step 2/5] Extracting raw facilities data to: {raw_csv_path}")
    extract_poi_to_csv(
        input_config["north"], input_config["south"], input_config["east"], input_config["west"],
        raw_csv_path,
        osm_file_path=osm_path
    )

    # Step 3: Classify Facilities + assign TAZ ID
    print(f"\n[Step 3/5] Classifying activities and saving to: {clean_csv_path}")
    classify_facilities(raw_csv_path, clean_csv_path, subdistricts_path=input_config["subdistricts_filename"])

    # Step 4: Assign Locations
    print(f"\n[Step 4/5] Assigning locations to trips: {final_trips_path}")
    if os.path.exists(trips_path):
        assign_facility_locations(trips_path, clean_csv_path, final_trips_path, target_size=input_config["sample_size"])
    else:
        print(f"[Note] {trips_path} not found. Skipping Step 4 & 5.")
        print(f"Please provide {input_config['trips_filename']} in the data/ folder.")
        end_time = time.time()
        print(f"\n=== Completed partially! Total time: {end_time - start_time:.2f} seconds ===")
        return

    # Step 5: Generate MATSim Plans
    print(f"\n[Step 5/5] Generating MATSim XML plans: {plans_path}")
    generate_matsim_plans(
        final_trips_path, 
        plans_path, 
        sample_size=input_config["sample_size"],
        bbox=(input_config["north"], input_config["south"], input_config["east"], input_config["west"])
    )

    # Step 6: Cut / fix agents (always runs — trims plans that don't end with home)
    cut_output_path = os.path.join(output_config["output_folder"], "plan_300k_cut.xml")
    print(f"\n[Step 6/6] Cutting & fixing agent plans: {cut_output_path}")
    fix_plan_home_end(plans_path, cut_output_path, dry_run=False)

    # Step 6b: Apply traffic conditions to network (optional)
    exec_config = config.get("execution", {})
    if exec_config.get("apply_traffic_conditions", False):
        conditions_file = exec_config.get("traffic_conditions_file", "data/traffic_conditions.json")
        print(f"\n[Step 6b] Applying traffic conditions from: {conditions_file}")
        result = load_conditions(conditions_file)
        if result is not None:
            input_network, output_network, conditions = result
            apply_conditions(input_network, output_network, conditions)
        else:
            print("[Step 6b] Skipped — could not load traffic conditions.")
    else:
        print("\n[Step 6b] Traffic conditions: skipped (set execution.apply_traffic_conditions=true to enable)")

    end_time = time.time()
    print(f"\n=== Preprocessing Completed! Total time: {end_time - start_time:.2f} seconds ===")
    print(f"Final output file: {cut_output_path}")

    # ==========================================
    # AUTO-EXECUTION MODULE (MATSim)
    # ==========================================
    if exec_config.get("run_simulation_automatically", False):
        print("\n=== Starting Automatic MATSim Execution ===")
        
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        maven_opts = exec_config.get("maven_opts", "-Xmx10G")
        matsim_config = exec_config.get("matsim_config_file", "bangkok_cbd_500k_config.xml")
        
        # Define the environment with custom MAVEN_OPTS
        env = os.environ.copy()
        env["MAVEN_OPTS"] = maven_opts
        
        # Detect OS for Maven Wrapper command
        if platform.system() == "Windows":
            maven_cmd = os.path.join(project_root, "mvnw.cmd")
        else:
            maven_cmd = os.path.join(project_root, "mvnw")

        if not os.path.exists(maven_cmd):
            print(f"[ERROR] ไม่พบ Maven Wrapper: {maven_cmd}")
            return

        # Step 6: Convert OSM
        print("\n[Step 6] Converting OSM to MATSim Network...")
        subprocess.run([maven_cmd, "exec:java", "-Dexec.mainClass=org.matsim.project.ConvertOSM"], cwd=project_root, env=env, check=True)

        # Step 7: Clean Network
        print("\n[Step 7] Cleaning Network...")
        subprocess.run([maven_cmd, "exec:java", "-Dexec.mainClass=org.matsim.project.RunNetworkCleaner"], cwd=project_root, env=env, check=True)

        # Step 8: Run MATSim
        print(f"\n[Step 8] Running MATSim with config: {matsim_config}...")
        subprocess.run([maven_cmd, "exec:java", "-Dexec.mainClass=org.matsim.project.RunMatsim", f"-Dexec.args={matsim_config}"], cwd=project_root, env=env, check=True)

        print("\n=== All processes completed successfully! ===")

if __name__ == "__main__":
    main()
