import pandas as pd
import xml.etree.ElementTree as ET
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer
import os
import random
from tqdm import tqdm

# Files
SOURCE_CSV = "../preprocess/data/final_trips.csv"
PLANS_XML = "../preprocess/output/plan.xml"
GEOJSON = "../preprocess/data/subdistricts_180.geojson"

SAMPLE_SIZE = 2000 # Increased sample for higher statistical confidence

def get_base_id(full_id):
    """Extracts the original ID from a cloned ID (e.g., '123_clone1' -> '123')."""
    return str(full_id).split('_clone')[0]

def validate_spatial_accuracy():
    print("="*60)
    print(" EVALUATION 2: SPATIAL ACCURACY (TAZ COMPLIANCE)")
    print("="*60)

    # 1. Load GeoJSON (The Map)
    if not os.path.exists(GEOJSON):
        print(f"Error: Map file {GEOJSON} not found.")
        return
    print(f"Loading TAZ Boundaries: {GEOJSON}...")
    subdistricts = gpd.read_file(GEOJSON)
    # Ensure WGS84 for point-in-polygon
    subdistricts = subdistricts.to_crs("EPSG:4326")

    # 2. Load Source Data (The Truth)
    print(f"Loading Source Demand: {SOURCE_CSV}...")
    df_src = pd.read_csv(SOURCE_CSV, usecols=['person_id', 'origin'], low_memory=False)
    # Convert to a fast lookup dictionary: {person_id: home_taz}
    taz_lookup = df_src.groupby('person_id')['origin'].first().to_dict()

    # 3. Sample Agents from XML (The Result)
    print(f"Sampling {SAMPLE_SIZE} agents from {PLANS_XML}...")
    
    # First pass: Collect all IDs
    all_ids = []
    try:
        context = ET.iterparse(PLANS_XML, events=('start',))
        for event, elem in context:
            if elem.tag == 'person':
                all_ids.append(elem.get('id'))
            elem.clear()
    except Exception as e:
        print(f"Error reading XML: {e}")
        return

    sampled_ids = random.sample(all_ids, min(len(all_ids), SAMPLE_SIZE))
    sampled_set = set(sampled_ids)

    # Second pass: Extract home coordinates for sampled agents
    print("Performing Point-in-Polygon checks...")
    transformer = Transformer.from_crs("EPSG:32647", "EPSG:4326", always_xy=True)
    
    hits = 0
    total = 0
    
    context = ET.iterparse(PLANS_XML, events=('start',))
    for event, elem in context:
        if elem.tag == 'person':
            pid = elem.get('id')
            if pid in sampled_set:
                # Get the first activity (Home)
                act = elem.find(".//activity")
                if act is not None:
                    x = float(act.get("x"))
                    y = float(act.get("y"))
                    
                    # A: Transform UTM -> WGS84
                    lon, lat = transformer.transform(x, y)
                    p = Point(lon, lat)
                    
                    # B: Identify which TAZ polygon contains this point
                    # We use a fast spatial query
                    containing_taz = subdistricts[subdistricts.contains(p)]
                    
                    if not containing_taz.empty:
                        sim_taz = int(containing_taz.iloc[0]['OBJECTID'])
                        
                        # C: Get target TAZ from source data (using base_id)
                        base_id = get_base_id(pid)
                        try:
                            # Cast base_id to int if the CSV has numeric IDs
                            key = int(base_id) if base_id.isdigit() else base_id
                            target_taz = int(taz_lookup.get(key, -1))
                            
                            if sim_taz == target_taz:
                                hits += 1
                        except:
                            pass
                    total += 1
            elem.clear()

    # 4. Final Report
    accuracy = (hits / total) * 100 if total > 0 else 0
    
    print("\n" + "-"*60)
    print(f"RESULTS SUMMARY")
    print("-"*60)
    print(f"Total Agents Checked:      {total:,}")
    print(f"Successful TAZ Matches:    {hits:,}")
    print(f"Spatial Accuracy Rate:     {accuracy:.2f}%")
    print("-"*60)
    
    if accuracy > 95:
        print("✅ SUCCESS: Tool accurately preserves spatial demand.")
    elif accuracy > 80:
        print("⚠️  CAUTION: Minor spatial drift detected (Check border facilities).")
    else:
        print("❌ FAILURE: Large spatial discrepancies found.")
    
    print("="*60)

if __name__ == "__main__":
    validate_spatial_accuracy()
