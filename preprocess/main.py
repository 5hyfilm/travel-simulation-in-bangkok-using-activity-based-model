import os
import time
from get_osm_network import download_osm_for_matsim
from get_facilities import extract_poi_to_csv
from process_facilities import classify_facilities
from assign_locations import assign_facility_locations
from generate_plans import generate_matsim_plans

def main():
    print("=== Starting MATSim data preparation process ===")

    input_config = {
        # Bounding box for Greater Bangkok
        "north": 13.96,
        "south": 13.49,
        "east":  100.96,
        "west":  100.33,
        "trips_filename": "data/final_trips.csv",
        "subdistricts_filename": "data/subdistricts_180.geojson",
        "sample_size": 500000  # Target population with cloning
    }

    output_config = {
        "output_folder": "output",
        "osm_filename": "network.osm",
        "raw_csv_filename": "facilities_raw.csv",
        "clean_csv_filename": "facilities_cleaned.csv",
        "final_trips_filename": "final_trips.csv",
        "plans_filename": "plan_all.xml",
    }

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
        assign_facility_locations(trips_path, clean_csv_path, final_trips_path)
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

    end_time = time.time()
    print(f"\n=== Completed! Total time: {end_time - start_time:.2f} seconds ===")
    print(f"Final output file: {plans_path}")

if __name__ == "__main__":
    main()
