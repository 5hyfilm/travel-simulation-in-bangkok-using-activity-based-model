# Installation & Setup

## 1. Prerequisites

- Python 3.9 or higher
- Internet connection (for Overpass API)

## 2. Set up Virtual Environment

Open your terminal or command prompt and run the following commands:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

## 3. Install Dependencies

Install the required Python libraries:

```bash
pip install -r requirements.txt
```

# How to Run

1. Open `main.py` and ensure the **Bounding Box (Coordinates)** matches your area of interest (Default is Siam/Pathum Wan, Bangkok).

   ```python
   config = {
       "north": 13.7480,
       "south": 13.7440,
       "east":  100.5370,
       "west":  100.5330,
       # ...
   }

   ```

2. Run the main script:

   ```bash
   python main.py
   ```

3. The script will execute the following steps automatically:
   - **[Step 1/3]:** Download `.osm` network file.
   - **[Step 2/3]:** Extract raw facilities to CSV.
   - **[Step 3/3]:** Clean names, classify activities, and generate H3 indices.

---

## 📂 Output Files

All results are saved in the `output/` folder:

| File Name                       | Description                                                                                                    |
| :------------------------------ | :------------------------------------------------------------------------------------------------------------- |
| **`network.osm`**               | Raw OpenStreetMap XML data (Highways, Buildings, Landuse).                                                     |
| **`facilities_raw.csv`**        | Raw POI data extracted directly from OSM.                                                                      |
| **`facilities_cleaned_h3.csv`** | **Final processed file**. Contains Activity Types, Cleaned Names, WGS84 Coordinates, and H3 Indices (Level 8). |

```

```
