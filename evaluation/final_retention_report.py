import pandas as pd
import xml.etree.ElementTree as ET
import os

def get_base_id(full_id):
    """Extracts the original ID from a cloned ID (e.g., '123_clone1' -> '123')."""
    return str(full_id).split('_clone')[0]

def generate_full_retention_report():
    files = {
        "Source (ActivitySim)": "../preprocess/data/final_trips.csv",
        "Assigned (Locations)": "../preprocess/output/final_trips.csv",
        "Final XML (MATSim)":   "../preprocess/output/plan.xml"
    }

    print("="*60)
    print(" PIPELINE DATA INTEGRITY & CONSISTENCY REPORT")
    print("="*60)

    # Sets to store unique IDs
    ids = {
        'source': set(),
        'assigned': set(),
        'xml': set()
    }

    # 1. Collect Source IDs
    if os.path.exists(files["Source (ActivitySim)"]):
        print(f"Reading {files['Source (ActivitySim)']}...")
        df = pd.read_csv(files["Source (ActivitySim)"], usecols=['person_id'], low_memory=False)
        ids['source'] = set(df['person_id'].astype(str).unique())
    else:
        print(f"Error: {files['Source (ActivitySim)']} not found.")

    # 2. Collect Assigned IDs
    if os.path.exists(files["Assigned (Locations)"]):
        print(f"Reading {files['Assigned (Locations)']}...")
        df = pd.read_csv(files["Assigned (Locations)"], usecols=['person_id'], dtype={'person_id': str})
        ids['assigned'] = set(df['person_id'].unique())
    else:
        print(f"Error: {files['Assigned (Locations)']} not found.")

    # 3. Collect XML IDs
    if os.path.exists(files["Final XML (MATSim)"]):
        print(f"Reading {files['Final XML (MATSim)']}...")
        try:
            for event, elem in ET.iterparse(files["Final XML (MATSim)"], events=('start',)):
                if elem.tag == 'person':
                    ids['xml'].add(elem.get('id'))
                elem.clear()
        except Exception as e:
            print(f"Error parsing XML: {e}")

    # --- Summary Table ---
    print("\n" + "-"*60)
    print(f"{'Pipeline Stage':<25} | {'Unique Agents':<15}")
    print("-"*60)
    print(f"{'1. Source Trip Data':<25} | {len(ids['source']):,}")
    print(f"{'2. Location Assigned':<25} | {len(ids['assigned']):,}")
    print(f"{'3. Final MATSim Plans':<25} | {len(ids['xml']):,}")
    print("-"*60)

    # --- Consistency Analysis ---
    print("\nID CONSISTENCY CHECK:")

    # Consistency A: Assigned -> Source
    # Every base ID in Assigned must be in Source
    if ids['assigned'] and ids['source']:
        base_ids_in_assigned = {get_base_id(pid) for pid in ids['assigned']}
        invalid_assigned = base_ids_in_assigned - ids['source']
        
        if not invalid_assigned:
            print(f"✅ Assigned Integrity: 100% (All {len(ids['assigned']):,} agents originate from the source dataset)")
        else:
            print(f"⚠️  Assigned Integrity: Found {len(invalid_assigned):,} foreign IDs not present in source!")

    # Consistency B: XML -> Assigned
    # Every ID in XML must have been in the Assigned file
    if ids['xml'] and ids['assigned']:
        missing_in_xml = ids['xml'] - ids['assigned']
        
        if not missing_in_xml:
            print(f"✅ XML Integrity:      100% (All {len(ids['xml']):,} agents in XML were correctly pre-assigned)")
        else:
            # Note: Sometimes IDs are cast to int in XML but strings in CSV, so we check both
            actual_missing = {mid for mid in missing_in_xml if str(mid) not in ids['assigned']}
            if not actual_missing:
                 print(f"✅ XML Integrity:      100% (All agents verified after type matching)")
            else:
                print(f"⚠️  XML Integrity:      Found {len(actual_missing):,} IDs in XML that were never pre-assigned!")

    # --- Volume Analysis ---
    print("\nPROJECTION ANALYSIS:")
    if len(ids['source']) > 0:
        scaling = (len(ids['assigned']) / len(ids['source'])) * 100
        print(f" -> Population Growth: {scaling:.1f}% (Scaling/Cloning)")
        
    if len(ids['assigned']) > 0:
        retention = (len(ids['xml']) / len(ids['assigned'])) * 100
        print(f" -> Process Retention: {retention:.1f}% (Sampling/Optimization)")

    print("="*60)

if __name__ == "__main__":
    generate_full_retention_report()
