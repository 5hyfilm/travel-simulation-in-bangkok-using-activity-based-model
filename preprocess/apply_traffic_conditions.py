"""
apply_traffic_conditions.py
===========================
อ่าน traffic_conditions.json แล้วปรับ freespeed และ capacity ของ links
ใน MATSim network file ตาม conditions ที่กำหนด

วิธีรัน (จาก project root):
    python preprocess/apply_traffic_conditions.py

หรือระบุ path ของ config เอง:
    python preprocess/apply_traffic_conditions.py data/traffic_conditions.json

ดูคำแนะนำการตั้งค่าได้ที่: data/traffic_conditions_guide.txt
"""

import sys
import json
import gzip
import shutil
import os
from lxml import etree

# ================================================================
# DEFAULT CONFIG PATH (แก้ได้ถ้าต้องการ)
# ================================================================
DEFAULT_CONDITIONS_FILE = "data/traffic_conditions.json"


def load_conditions(conditions_file):
    """โหลดและ validate traffic_conditions.json"""
    if not os.path.exists(conditions_file):
        print(f"!!! ไม่พบไฟล์: {conditions_file}")
        print(f"    กรุณาสร้างไฟล์ หรือดูตัวอย่างที่ data/traffic_conditions_guide.txt")
        return None

    with open(conditions_file, encoding="utf-8") as f:
        data = json.load(f)

    # อ่าน paths
    paths = data.get("paths", {})
    input_network  = paths.get("input_network",  "data/processed/network.cleaned.xml.gz")
    output_network = paths.get("output_network", "data/processed/network_traffic.xml.gz")

    # อ่าน conditions
    conditions = data.get("conditions", [])
    if not conditions:
        print("!!! ไม่มี conditions ใน JSON")
        return None

    return input_network, output_network, conditions


def validate_condition(cond):
    """ตรวจสอบค่าใน condition ว่าถูกต้องไหม"""
    name = cond.get("name", "unnamed")
    speed    = cond.get("speed_factor", 1.0)
    capacity = cond.get("capacity_factor", 1.0)
    errors = []

    if not (0.01 <= speed <= 1.0):
        errors.append(f"speed_factor={speed} ต้องอยู่ระหว่าง 0.01–1.0")
    if not (0.0 <= capacity <= 1.0):
        errors.append(f"capacity_factor={capacity} ต้องอยู่ระหว่าง 0.0–1.0")
    if "road_types" not in cond and "link_id" not in cond:
        errors.append("ต้องมี 'road_types' หรือ 'link_id' อย่างใดอย่างหนึ่ง")

    if errors:
        for e in errors:
            print(f"  ⚠️  [{name}] {e}")
        return False
    return True


def apply_conditions(input_network, output_network, conditions):
    """อ่าน network XML, apply conditions, เขียน output"""

    if not os.path.exists(input_network):
        print(f"!!! ไม่พบ network file: {input_network}")
        return

    print(f"\nอ่าน network: {input_network}")

    # แตก gz แล้ว parse XML
    with gzip.open(input_network, "rb") as f:
        tree = etree.parse(f)

    root = tree.getroot()
    links_elem = root.find("links")
    if links_elem is None:
        print("!!! ไม่พบ <links> ใน network XML")
        return

    all_links = links_elem.findall("link")
    print(f"พบ links ทั้งหมด: {len(all_links):,} links")

    total_modified = 0

    for cond in conditions:
        name           = cond.get("name", "unnamed")
        speed_factor   = cond.get("speed_factor", 1.0)
        cap_factor     = cond.get("capacity_factor", 1.0)
        road_types     = cond.get("road_types", [])
        link_id_target = cond.get("link_id", None)

        if not validate_condition(cond):
            continue

        modified = 0

        # --- กรณี 1: ระบุ link_id เฉพาะจุด ---
        if link_id_target:
            found = False
            for link in all_links:
                if link.get("id") == str(link_id_target):
                    orig_speed = float(link.get("freespeed", 0))
                    orig_cap   = float(link.get("capacity", 0))
                    link.set("freespeed", f"{orig_speed * speed_factor:.4f}")
                    link.set("capacity",  f"{orig_cap   * cap_factor:.4f}")
                    modified = 1
                    found = True
                    break
            if not found:
                print(f"  ⚠️  [{name}] link_id '{link_id_target}' ไม่พบใน network")

        # --- กรณี 2: ระบุ road_types ---
        elif road_types:
            for link in all_links:
                # หา type attribute จาก <attributes> ภายใน <link>
                link_type = None
                attrs_elem = link.find("attributes")
                if attrs_elem is not None:
                    for attr in attrs_elem.findall("attribute"):
                        if attr.get("name") == "type":
                            link_type = attr.text
                            break

                if link_type in road_types:
                    orig_speed = float(link.get("freespeed", 0))
                    orig_cap   = float(link.get("capacity", 0))
                    link.set("freespeed", f"{orig_speed * speed_factor:.4f}")
                    link.set("capacity",  f"{orig_cap   * cap_factor:.4f}")
                    modified += 1

        total_modified += modified
        print(f"  ✅ [{name}] speed×{speed_factor}, capacity×{cap_factor} → {modified:,} links ถูกปรับ")

    print(f"\nรวม links ที่ถูกปรับ: {total_modified:,} / {len(all_links):,}")

    # เขียน output
    os.makedirs(os.path.dirname(output_network), exist_ok=True)
    with gzip.open(output_network, "wb") as f:
        tree.write(f, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    print(f"✅ บันทึก network ใหม่ที่: {output_network}")
    print(f"\n👉 อย่าลืมแก้ config.xml ให้ชี้ไปที่ network ใหม่:")
    print(f'   <param name="inputNetworkFile" value="processed/network_traffic.xml.gz"/>')


def main():
    # รับ path ของ conditions file จาก argument หรือใช้ default
    conditions_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONDITIONS_FILE

    print("=" * 60)
    print("  Apply Traffic Conditions to MATSim Network")
    print(f"  Config: {conditions_file}")
    print(f"  (ดูคำแนะนำ: data/traffic_conditions_guide.txt)")
    print("=" * 60)

    result = load_conditions(conditions_file)
    if result is None:
        return

    input_network, output_network, conditions = result
    print(f"\nInput network : {input_network}")
    print(f"Output network: {output_network}")
    print(f"Conditions    : {len(conditions)} รายการ")

    apply_conditions(input_network, output_network, conditions)
    print("\n=== เสร็จสิ้น ===")


if __name__ == "__main__":
    main()
