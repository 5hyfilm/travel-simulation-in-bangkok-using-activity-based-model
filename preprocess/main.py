import os
import time
from get_osm_network import download_osm_for_matsim
from get_facilities import extract_poi_to_csv
from process_facilities import classify_facilities  # <--- เพิ่มบรรทัดนี้

def main():
    print("=== Starting MATSim data preparation process ===")

    config = {
        "north": 13.7480,
        "south": 13.7440,
        "east":  100.5370,
        "west":  100.5330,
        "output_folder": "output",
        "osm_filename": "network.osm",
        "raw_csv_filename": "facilities_raw.csv",       # เปลี่ยนชื่อเป็น raw เพื่อกันสับสน
        "clean_csv_filename": "facilities_cleaned.csv"  # ไฟล์ผลลัพธ์สุดท้าย
    }

    if not os.path.exists(config["output_folder"]):
        os.makedirs(config["output_folder"], exist_ok=True)

    osm_path = os.path.join(config["output_folder"], config["osm_filename"])
    raw_csv_path = os.path.join(config["output_folder"], config["raw_csv_filename"])
    clean_csv_path = os.path.join(config["output_folder"], config["clean_csv_filename"])

    start_time = time.time()

    # Step 1: Download Map
    print(f"\n[Step 1/3] Downloading map network to: {osm_path}")
    download_osm_for_matsim(
        config["north"], config["south"], config["east"], config["west"], 
        osm_path
    )

    # Step 2: Extract Raw Facilities
    print(f"\n[Step 2/3] Extracting raw facilities data to: {raw_csv_path}")
    extract_poi_to_csv(
        config["north"], config["south"], config["east"], config["west"], 
        raw_csv_path,
        osm_file_path=osm_path
    )

    # Step 3: Classify Facilities (ขั้นตอนใหม่)
    print(f"\n[Step 3/3] Classifying activities and saving to: {clean_csv_path}")
    classify_facilities(raw_csv_path, clean_csv_path)

    end_time = time.time()
    print(f"\n=== Completed! Total time: {end_time - start_time:.2f} seconds ===")
    print(f"Final output file: {clean_csv_path}")

if __name__ == "__main__":
    main()