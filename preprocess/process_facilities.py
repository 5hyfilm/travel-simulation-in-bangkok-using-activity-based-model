import pandas as pd
import numpy as np
import h3
import re

def classify_facilities(input_csv, output_csv, h3_resolution=8):
    """
    Read raw CSV file, classify Activity Types, 
    clean names for MATSim compatibility,
    create H3 Grid Index, and prepare WGS84 coordinates (x, y).
    
    Parameters:
    - h3_resolution: Grid resolution (9 = ~0.1 sq km, 8 = ~0.7 sq km)
      ** Default set to 8 **
    """
    print(f"Processing data from: {input_csv}...")
    
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"!!! Cannot open file: {e}")
        return

    # --- Helper: Name Cleaning Function ---
    def clean_name_for_matsim(name):
        if pd.isna(name):
            return name
        name = str(name)
        
        # 1. Replace common symbols that have meaning
        name = name.replace('&', ' and ')
        name = name.replace('@', ' at ')
        name = name.replace('+', ' plus ')
        
        # 2. Remove XML breaking characters and other confusing symbols
        # Remove: " ' < > / \ | ? * ; :
        name = re.sub(r'["\'<>/\\|?*;:]', '', name)
        
        # 3. Remove non-printable characters or excessive whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name

    # --- 1. Classification Logic ---
    def get_type(row):
        # 1. Shopping
        if pd.notna(row.get('shop')): return 'shopping'
        
        # 2. Dining
        dining = ['restaurant', 'cafe', 'fast_food', 'bar', 'pub', 'food_court']
        if row.get('amenity') in dining: return 'dining'
        
        # 3. Park
        if row.get('leisure') in ['park', 'garden', 'playground']: return 'park'
        
        # 4. Leisure
        leisure = ['cinema', 'theatre', 'museum', 'arts_centre', 'aquarium']
        if pd.notna(row.get('leisure')) or row.get('amenity') in leisure: return 'leisure'
        
        # 5. Education
        if row.get('amenity') in ['school', 'university', 'library'] or row.get('building') == 'school': return 'education'
        
        # 6. Religion
        if row.get('building') in ['temple', 'church', 'mosque'] or row.get('amenity') == 'place_of_worship': return 'religion'
        
        # 7. Public Service
        public = ['bank', 'hospital', 'police', 'post_office', 'clinic', 'atm']
        if row.get('building') == 'government' or row.get('amenity') in public: return 'public_service'
        
        # 8. Work
        work = ['commercial', 'office', 'industrial', 'warehouse']
        if pd.notna(row.get('office')) or row.get('building') in work: return 'work'
        
        # 9. Home
        home = ['residential', 'apartments', 'house', 'terrace']
        if row.get('building') in home: return 'home'
        if row.get('building') == 'yes' and pd.isna(row.get('name')): return 'home'
        
        # 10. Transit
        transit = ['bus_station', 'parking', 'parking_entrance', 'ferry_terminal']
        if row.get('amenity') in transit: return 'transit'
        
        return 'other'

    print("Classifying activities...")
    df['activity_type'] = df.apply(get_type, axis=1)

    # --- Handle ID and Name ---
    if 'osmid' not in df.columns:
        df['osmid'] = range(1, len(df) + 1)
    
    # Fill missing names
    df['name'] = df.apply(
        lambda x: x['name'] if pd.notna(x['name']) else f"Unnamed_{x['activity_type']}_{x['osmid']}", 
        axis=1
    )

    # Apply Cleaning to Names
    print("Cleaning facility names for MATSim compatibility...")
    df['name'] = df['name'].apply(clean_name_for_matsim)

    # --- 2. Coordinate Preparation for MATSim & H3 ---
    print(f"Processing coordinates (WGS84) and H3 Grid (Res {h3_resolution})...")

    # 2.1 Add x, y columns (MATSim Standard: x=longitude, y=latitude)
    df['x'] = df['longitude']
    df['y'] = df['latitude']

    # 2.2 Add coordinate tuple column (Longitude, Latitude) or (x, y)
    df['wgs84_coords'] = list(zip(df['x'], df['y']))

    # 2.3 Create H3 Index
    def get_h3(row):
        try:
            return h3.latlng_to_cell(row['y'], row['x'], h3_resolution)
        except:
            return None
            
    df['h3_index'] = df.apply(get_h3, axis=1)

    # Select columns to save
    final_cols = [
        'osmid', 'name', 'activity_type', 
        'x', 'y',               # Separate coordinates (for MATSim XML)
        'wgs84_coords',         # Combined coordinates (Tuple)
        'h3_index',             # H3 Grid
        'latitude', 'longitude' # Keep original columns for reference
    ]
    
    final_df = df[final_cols]
    
    final_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"✅ Successfully saved cleaned data to: {output_csv}")
    print("-" * 30)
    
    # Use to_string instead of to_markdown
    print(final_df[['name', 'activity_type', 'x', 'y', 'wgs84_coords']].head().to_string(index=False)) 
    print("-" * 30)
    print(final_df['activity_type'].value_counts())

if __name__ == "__main__":
    classify_facilities('facilities_raw.csv', 'facilities_cleaned_h3.csv', h3_resolution=8)