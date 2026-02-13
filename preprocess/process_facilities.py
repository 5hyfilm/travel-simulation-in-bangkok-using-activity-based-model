import pandas as pd
import numpy as np
import h3  # pip install h3

def classify_facilities(input_csv, output_csv, h3_resolution=9):
    """
    อ่านไฟล์ CSV ดิบ, จัดกลุ่ม (Activity Types), 
    สร้าง H3 Grid Index และเตรียมพิกัด WGS84 (x, y) สำหรับ MATSim
    """
    print(f"กำลังประมวลผลข้อมูลจาก: {input_csv}...")
    
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"!!! ไม่สามารถเปิดไฟล์ได้: {e}")
        return

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

    df['activity_type'] = df.apply(get_type, axis=1)

    # จัดการ ID และ ชื่อ
    if 'osmid' not in df.columns:
        df['osmid'] = range(1, len(df) + 1)
    
    df['name'] = df.apply(
        lambda x: x['name'] if pd.notna(x['name']) else f"Unnamed_{x['activity_type']}_{x['osmid']}", 
        axis=1
    )

    # --- 2. Coordinate Preparation for MATSim & H3 ---
    print(f"Processing coordinates (WGS84) and H3 Grid (Res {h3_resolution})...")

    # 2.1 เพิ่ม column x, y (MATSim Standard: x=longitude, y=latitude)
    df['x'] = df['longitude']
    df['y'] = df['latitude']

    # 2.2 เพิ่ม column พิกัดแบบ Tuple (Longitude, Latitude) หรือ (x, y)
    # คอลัมน์นี้ระบุว่าเป็น 'wgs84_coords' ชัดเจน
    df['wgs84_coords'] = list(zip(df['x'], df['y']))

    # 2.3 สร้าง H3 Index
    def get_h3(row):
        try:
            return h3.latlng_to_cell(row['y'], row['x'], h3_resolution)
        except:
            return None
            
    df['h3_index'] = df.apply(get_h3, axis=1)

    # เลือก Column ที่จะบันทึก (เพิ่ม x, y และ wgs84_coords)
    final_cols = [
        'osmid', 'name', 'activity_type', 
        'x', 'y',               # พิกัดแยก (สำหรับ MATSim XML)
        'wgs84_coords',         # พิกัดรวม (Tuple)
        'h3_index',             # H3 Grid
        'latitude', 'longitude' # เก็บตัวเดิมไว้ด้วยเผื่อใช้
    ]
    
    final_df = df[final_cols]
    
    final_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"✅ บันทึกข้อมูลเรียบร้อยแล้วไปที่: {output_csv}")
    print("-" * 30)
    # ใช้ to_string แทน to_markdown เพื่อลด dependency
    print(final_df[['name', 'activity_type', 'x', 'y', 'wgs84_coords']].head().to_string(index=False)) 
    print("-" * 30)
    print(final_df['activity_type'].value_counts())

if __name__ == "__main__":
    classify_facilities('facilities_raw.csv', 'facilities_cleaned_h3.csv', h3_resolution=9)