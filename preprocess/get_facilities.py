import osmnx as ox
import pandas as pd

def extract_poi_to_csv(north, south, east, west, filename="poi_data.csv", osm_file_path=None):
    """
    Extract Points of Interest (POI) from OSM file or API and save as CSV
    """
    print(f"Extracting facilities data...")
    
    tags = {
        'amenity': True,
        'building': True,
        'shop': True,
        'office': True,
        'leisure': True,
        'tourism': True
    }

    try:
        # Load from existing .osm file to avoid coordinate calculation errors
        if osm_file_path:
            print(f"Reading from file: {osm_file_path}")
            gdf = ox.features.features_from_xml(osm_file_path, tags=tags)
        else:
            # Fallback to API download
            gdf = ox.features.features_from_bbox(bbox=(north, south, east, west), tags=tags)
        
        if gdf.empty:
            print("No facilities found in the specified area.")
            return

        print(f"Found {len(gdf)} facilities.")

        # Reset index to include osmid as a column
        poi_df = gdf.reset_index()
        
        # Calculate centroids for Lat/Lon
        poi_df['latitude'] = poi_df.geometry.centroid.y
        poi_df['longitude'] = poi_df.geometry.centroid.x

        columns_to_keep = ['osmid', 'name', 'amenity', 'building', 'shop', 'office', 'leisure', 'latitude', 'longitude']
        existing_cols = [c for c in columns_to_keep if c in poi_df.columns]
        final_df = poi_df[existing_cols]

        final_df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"Successfully saved facilities to: {filename}")
        print("-" * 30)

    except Exception as e:
        print(f"!!! Error occurred: {e}")