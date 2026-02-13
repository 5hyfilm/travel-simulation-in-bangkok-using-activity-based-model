import requests

def download_osm_for_matsim(north, south, east, west, filename="map_data.osm"):
    """
    Download Raw OSM (XML) data from Overpass API for use with MATSim
    Updated: Uses specific query for highway, building, and landuse only.
    """
    
    # URL of Overpass API (Public Server)
    api_url = "https://overpass-api.de/api/interpreter"

    # Create Overpass QL Query
    # Logic:
    # 1. Select ways that are highways, buildings, or landuse within bbox.
    # 2. Output the ways (out body).
    # 3. Recurse down (>;) to get the nodes used by those ways.
    # 4. Output nodes as skeleton (out skel qt) to save space.
    query = f"""
    [out:xml][timeout:180];
    (
      way["highway"]({south},{west},{north},{east});
      way["building"]({south},{west},{north},{east});
      way["landuse"]({south},{west},{north},{east});
    );
    out body;
    >;
    out skel qt;
    """

    print(f"Downloading optimized .osm data for coordinates: N={north}, S={south}, E={east}, W={west}...")
    print("Querying for: Highway, Building, Landuse...")

    try:
        # Send Request to API
        response = requests.post(api_url, data={'data': query})
        
        # Check if successful (Status 200 = OK)
        if response.status_code == 200:
            # Save content as .osm file
            with open(filename, 'wb') as file:
                file.write(response.content)
            print(f"Success! File saved at: {filename}")
            print(f"File size: {len(response.content) / 1024:.2f} KB")
        else:
            print(f"Server Error: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Connection Error: {e}")

# Test run (optional)
if __name__ == "__main__":
    download_osm_for_matsim(13.7480, 13.7440, 100.5370, 100.5330)