import json
import subprocess
import os
from pathlib import Path

# --- ตั้งค่า Paths ---
# สมมติว่ารันสคริปต์จาก Project Root
BASE_DIR = Path.cwd()
MASTER_JSON = BASE_DIR / "evaluation" / "network_paths" / "config_corridors_from_network.json"
LINKS_CSV = BASE_DIR / "output" / "output_links.csv.gz"
CONFIG_DIR = BASE_DIR / "evaluation" / "network_paths"
OUTPUT_DIR = BASE_DIR / "evaluation" / "geojson"
EXPORT_SCRIPT = BASE_DIR / "evaluation" / "export_corridor_geojson.py" # ชื่อไฟล์สคริปต์ที่คุณให้มา

# สร้างโฟลเดอร์ output ถ้ายังไม่มี
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run_batch_export():
    # 1. อ่านไฟล์ Master JSON เพื่อเอา Corridor IDs ทั้งหมด
    if not MASTER_JSON.exists():
        print(f"Error: Not found master JSON at {MASTER_JSON}")
        return

    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    corridors = data.get("corridors", [])
    print(f"Found {len(corridors)} corridors in master config.")

    # 2. วนลูปประมวลผลทีละเส้นทาง
    for corridor in corridors:
        c_id = corridor["corridor_id"]
        
        # ค้นหาไฟล์ fragment ที่ตรงกับ id
        config_fragment = CONFIG_DIR / f"{c_id}_config_fragment.json"
        output_file = OUTPUT_DIR / f"{c_id}.geojson"

        if not config_fragment.exists():
            print(f"[-] Skipping {c_id}: Fragment file not found at {config_fragment}")
            continue

        print(f"[+] Exporting: {c_id}...")

        # 3. เรียกใช้สคริปต์ export_corridor_geojson.py
        # ใช้ Arguments ตามที่สคริปต์ต้นฉบับกำหนด (--links, --config-fragment, --out)
        cmd = [
            "python", str(EXPORT_SCRIPT),
            "--links", str(LINKS_CSV),
            "--config-fragment", str(config_fragment),
            "--out", str(output_file)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # แสดงผลลัพธ์จากสคริปต์หลัก (จำนวน Features ที่บันทึกได้)
            for line in result.stdout.splitlines():
                if "Saved GeoJSON" in line or "Feature count" in line:
                    print(f"    {line}")
        except subprocess.CalledProcessError as e:
            print(f"    [!] Error processing {c_id}:")
            print(f"    {e.stderr}")

    print("\n--- All export processes completed ---")

if __name__ == "__main__":
    run_batch_export()