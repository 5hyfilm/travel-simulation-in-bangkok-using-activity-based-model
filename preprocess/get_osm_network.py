import requests

def download_osm_for_matsim(north, south, east, west, filename="map_data.osm"):
    """
    Download Raw OSM (XML) data from Overpass API for use with MATSim
    """
    
    # URL of Overpass API (Public Server)
    api_url = "https://overpass-api.de/api/interpreter"

    # Create Overpass QL Query
    # This query fetches all Nodes, Ways, and Relations within the bounding box
    # and includes all related components (recursion) for a complete XML output.
    query = f"""
    [out:xml][timeout:180];
    (
      node({south},{west},{north},{east});
      way({south},{west},{north},{east});
      relation({south},{west},{north},{east});
    );
    (._;>;);
    out meta;
    """

    print(f"Downloading .osm data for coordinates: N={north}, S={south}, E={east}, W={west}...")
    print("This may take a moment depending on the area size...")

    try:
        # Send Request to API
        response = requests.post(api_url, data={'data': query})
        
        # Check if successful (Status 200 = OK)
        if response.status_code == 200:
            # Save content as .osm file
            # Write in binary mode (wb) to correctly handle UTF-8 XML encoding
            with open(filename, 'wb') as file:
                file.write(response.content)
            print(f"Success! File saved at: {filename}")
            print(f"File size: {len(response.content) / 1024:.2f} KB")
        else:
            print(f"Server Error: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Connection Error: {e}")