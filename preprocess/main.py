import os
import time
from get_osm_network import download_osm_for_matsim
from get_facilities import extract_poi_to_csv

def main():
    # "=== Starting MATSim data preparation process ==="
    print("=== Starting MATSim data preparation process ===")

    config = {
        "north": 13.7480,
        "south": 13.7440,
        "east":  100.5370,
        "west":  100.5330,
        "output_folder": "output",
        "osm_filename": "network.osm",
        "csv_filename": "facilities.csv"
    }

    if not os.path.exists(config["output_folder"]):
        os.makedirs(config["output_folder"], exist_ok=True)

    osm_path = os.path.join(config["output_folder"], config["osm_filename"])
    csv_path = os.path.join(config["output_folder"], config["csv_filename"])

    start_time = time.time()

    # Step 1: Download Map
    # "[Step 1/2] Downloading map network to: ..."
    print(f"\n[Step 1/2] Downloading map network to: {osm_path}")
    download_osm_for_matsim(
        config["north"], config["south"], config["east"], config["west"], 
        osm_path
    )

    # Step 2: Extract CSV Facilities
    # "[Step 2/2] Extracting facilities data from file: ..."
    print(f"\n[Step 2/2] Extracting facilities data from file: {osm_path}")
    extract_poi_to_csv(
        config["north"], config["south"], config["east"], config["west"], 
        csv_path,
        osm_file_path=osm_path
    )

    end_time = time.time()
    # "=== Completed! Total time: ... seconds ==="
    print(f"\n=== Completed! Total time: {end_time - start_time:.2f} seconds ===")

if __name__ == "__main__":
    main()