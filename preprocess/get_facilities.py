import osmnx as ox
import pandas as pd
import os
import traceback
import sys

# แสดงข้อมูลพื้นฐานก่อนเพื่อ debug
print("Python version:", sys.version)
print("OSMnx version:", ox.__version__)
print("Current directory:", os.getcwd())

def extract_poi_to_csv(north, south, east, west, filename="poi_data.csv", osm_file_path=None):
    print("\n=== Starting POI extraction ===")
    
    tags = {
        'amenity': True,
        'building': True,
        'shop': True,
        'office': True,
        'leisure': True,
        'tourism': True
    }

    try:
        if osm_file_path:
            print(f"Reading from OSM file: {osm_file_path}")
            if not os.path.exists(osm_file_path):
                raise FileNotFoundError(f"ไม่พบไฟล์: {osm_file_path}")
            gdf = ox.features.features_from_xml(osm_file_path, tags=tags)
        else:
            # สำคัญ! ใน osmnx 2.x ต้องใช้ bbox = (west, south, east, north)
            bbox = (west, south, east, north)
            print(f"Downloading from Overpass API → bbox (west, south, east, north): {bbox}")
            gdf = ox.features.features_from_bbox(bbox=bbox, tags=tags)

        if gdf is None or len(gdf) == 0:
            print("No facilities found in this area.")
            return

        print(f"Found {len(gdf)} facilities.")

        # Reset index และคำนวณพิกัด
        poi_df = gdf.reset_index()
        poi_df['latitude'] = poi_df.geometry.centroid.y
        poi_df['longitude'] = poi_df.geometry.centroid.x

        # เลือกคอลัมน์ที่ต้องการ
        columns_to_keep = ['osmid', 'name', 'amenity', 'building', 'shop', 
                          'office', 'leisure', 'latitude', 'longitude']
        existing_cols = [c for c in columns_to_keep if c in poi_df.columns]
        final_df = poi_df[existing_cols]

        final_df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✅ Successfully saved {len(final_df)} rows to: {os.path.abspath(filename)}")

    except Exception as e:
        print(f"!!! ERROR: {type(e).__name__} - {e}")
        traceback.print_exc()


# ===================== เรียกใช้ฟังก์ชัน =====================
if __name__ == "__main__":
    print("Script started...")

    # ทดสอบด้วยพื้นที่เล็ก ๆ ก่อน (แนะนำมาก)
    extract_poi_to_csv(
        north=13.7563,   # lat เหนือ
        south=13.7520,   # lat ใต้
        east=100.5020,   # lon ตะวันออก
        west=100.4980,   # lon ตะวันตก
        filename="poi_bangkok_test.csv"
    )