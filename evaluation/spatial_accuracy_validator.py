import gzip
import pandas as pd
import xml.etree.ElementTree as ET
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer
import os
import sys

# Auto-detect Project Root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files
SOURCE_CSV = os.path.join(BASE_DIR, "pipeline/data/final_trips.csv")
PLANS_XML = os.path.join(BASE_DIR, "normal_output", "output", "output_plans.xml.gz")
GEOJSON = os.path.join(BASE_DIR, "pipeline/data/subdistricts_180.geojson")

def get_base_id(full_id):
    return str(full_id).split('_clone')[0]

def validate_full_spatial_accuracy():
    print("="*70)
    print(" EVALUATION 2 (FULL POPULATION): SPATIAL ACCURACY (TAZ COMPLIANCE)")
    print("="*70)

    # 1. Load GeoJSON
    print(f"Loading TAZ Boundaries: {GEOJSON}...")
    subdistricts = gpd.read_file(GEOJSON)[['OBJECTID', 'geometry']]
    subdistricts = subdistricts.to_crs("EPSG:4326")

    # 2. Load Source Data (The Truth)
    print(f"Loading Source Demand: {SOURCE_CSV}...")
    df_src = pd.read_csv(SOURCE_CSV, usecols=['person_id', 'origin'], low_memory=False)
    # Fast lookup dictionary
    taz_lookup = df_src.groupby('person_id')['origin'].first().to_dict()

    # 3. Extract ALL Agents from XML
    print(f"Extracting all agents from {PLANS_XML}...")
    agent_list = []
    
    try:
        with gzip.open(PLANS_XML, 'rb') as gz_file:
            context = ET.iterparse(gz_file, events=('end',))
            for event, elem in context:
                if elem.tag == 'person':
                    pid = elem.get('id')
                    plan = elem.find("plan")
                    if plan is not None:
                        act = plan.find("activity")
                        if act is not None:
                            agent_list.append({
                                "person_id": pid,
                                "x": float(act.get("x")),
                                "y": float(act.get("y"))
                            })
                    elem.clear()
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return

    print(f"  > Successfully extracted {len(agent_list):,} agents.")

    # 4. Vectorized Spatial Processing
    print("Performing Vectorized Spatial Join (this may take 1-2 minutes)...")
    df_xml = pd.DataFrame(agent_list)
    
    # A: Bulk Transform UTM -> WGS84
    transformer = Transformer.from_crs("EPSG:32647", "EPSG:4326", always_xy=True)
    lons, lats = transformer.transform(df_xml['x'].values, df_xml['y'].values)
    
    # B: Create GeoDataFrame
    geometry = [Point(xy) for xy in zip(lons, lats)]
    gdf_xml = gpd.GeoDataFrame(df_xml, geometry=geometry, crs="EPSG:4326")
    
    # C: Spatial Join with TAZ Polygons
    gdf_joined = gpd.sjoin(gdf_xml, subdistricts, how='left', predicate='within')

    # 5. Accuracy Comparison
    print("Calculating final accuracy metrics...")
    
    def check_match(row):
        base_id = get_base_id(row['person_id'])
        # Handle type matching
        key = int(base_id) if base_id.isdigit() else base_id
        target_taz = taz_lookup.get(key)
        
        if pd.isna(row['OBJECTID']) or target_taz is None:
            return False
        return int(row['OBJECTID']) == int(target_taz)

    results = gdf_joined.apply(check_match, axis=1)
    hits = results.sum()
    total = len(results)
    accuracy = (hits / total) * 100 if total > 0 else 0

    # 6. Final Report
    print("\n" + "-"*70)
    print(f"FULL POPULATION RESULTS SUMMARY")
    print("-"*70)
    print(f"Total Agents Simulated:    {total:,}")
    print(f"Successful TAZ Matches:    {hits:,}")
    print(f"Spatial Accuracy Rate:     {accuracy:.2f}%")
    print("="*70)

if __name__ == "__main__":
    validate_full_spatial_accuracy()