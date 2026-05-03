"""
apply_traffic_conditions.py
===========================
Read traffic_conditions.json and adjust freespeed and capacity of links
in a MATSim network file according to the defined conditions.

Run from project root:
    python pipeline/apply_traffic_conditions.py

Or specify a custom config path:
    python pipeline/apply_traffic_conditions.py data/traffic_conditions.json

See setup guide at: data/traffic_conditions_guide.txt
"""

import sys
import json
import gzip
import shutil
import os
from lxml import etree

# ================================================================
# DEFAULT CONFIG PATH
# ================================================================
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_CONDITIONS_FILE = os.path.join(_PROJECT_ROOT, "data/traffic_conditions.json")


def _resolve(path, root):
    """Resolve a path relative to project root if it is not absolute."""
    if os.path.isabs(path):
        return path
    return os.path.join(root, path)


def load_conditions(conditions_file, project_root=None):
    """Load and validate traffic_conditions.json.

    Parameters
    ----------
    conditions_file : str
        Path to the JSON file (absolute or relative to project root).
    project_root : str, optional
        Project root directory used to resolve relative paths inside the JSON.
        Defaults to the parent of this script's directory.
    """
    if project_root is None:
        project_root = _PROJECT_ROOT

    if not os.path.exists(conditions_file):
        print(f"!!! File not found: {conditions_file}")
        print(f"    Please create the file or see example at data/traffic_conditions_guide.txt")
        return None

    with open(conditions_file, encoding="utf-8") as f:
        data = json.load(f)

    # Read paths — resolve relative paths against the project root
    paths = data.get("paths", {})
    input_network  = _resolve(paths.get("input_network",  "data/processed/network.xml.gz"),  project_root)
    output_network = _resolve(paths.get("output_network", "data/processed/network_condition.xml.gz"), project_root)

    # Read conditions
    conditions = data.get("conditions", [])
    if not conditions:
        print("!!! No conditions found in JSON")
        return None

    return input_network, output_network, conditions


def validate_condition(cond):
    """Validate values in a condition entry."""
    name     = cond.get("name", "unnamed")
    speed    = cond.get("speed_factor", 1.0)
    capacity = cond.get("capacity_factor", 1.0)
    errors   = []

    if not (0.01 <= speed <= 1.0):
        errors.append(f"speed_factor={speed} must be between 0.01 and 1.0")
    if not (0.0 <= capacity <= 1.0):
        errors.append(f"capacity_factor={capacity} must be between 0.0 and 1.0")
    if "road_types" not in cond and "link_id" not in cond:
        errors.append("must have either 'road_types' or 'link_id'")

    if errors:
        for e in errors:
            print(f"  ⚠️  [{name}] {e}")
        return False
    return True


def apply_conditions(input_network, output_network, conditions):
    """Read network XML, apply conditions, write output."""

    if not os.path.exists(input_network):
        print(f"!!! Network file not found: {input_network}")
        return

    # Check the gzip file is not truncated before parsing
    try:
        with gzip.open(input_network, "rb") as _test:
            while _test.read(65536):
                pass
    except EOFError:
        print(f"!!! Network file is corrupted (truncated gzip): {input_network}")
        print(f"    This usually means a previous write was interrupted.")
        print(f"    Fix: re-run the OSM → MATSim network conversion to regenerate the file.")
        print(f"    (ConvertOSM step in Maven, or delete the file and run main.py again)")
        return
    except Exception as e:
        print(f"!!! Could not read network file: {e}")
        return

    print(f"\nReading network: {input_network}")

    # Parse gzipped XML
    with gzip.open(input_network, "rb") as f:
        tree = etree.parse(f)

    root = tree.getroot()
    links_elem = root.find("links")
    if links_elem is None:
        print("!!! No <links> element found in network XML")
        return

    all_links = links_elem.findall("link")
    print(f"Total links found: {len(all_links):,}")

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

        # --- Case 1: target a specific link_id ---
        if link_id_target:
            found = False
            for link in all_links:
                if link.get("id") == str(link_id_target):
                    if cap_factor == 0.0:
                        # Remove the link entirely — Hermes ignores capacity=0
                        # and still lets vehicles through; removal is the only
                        # way to prevent routing + traversal completely.
                        links_elem.remove(link)
                        modified = 1
                        print(f"  🚫 [{name}] link '{link_id_target}' REMOVED from network (road closure)")
                    else:
                        orig_speed = float(link.get("freespeed", 0))
                        orig_cap   = float(link.get("capacity", 0))
                        link.set("freespeed", f"{orig_speed * speed_factor:.4f}")
                        link.set("capacity",  f"{orig_cap   * cap_factor:.4f}")
                        modified = 1
                    found = True
                    break
            if not found:
                print(f"  ⚠️  [{name}] link_id '{link_id_target}' not found in network")

        # --- Case 2: target by road_types ---
        elif road_types:
            # Refresh list after possible removals above
            for link in list(links_elem.findall("link")):
                # Find type attribute inside <attributes> block
                link_type  = None
                attrs_elem = link.find("attributes")
                if attrs_elem is not None:
                    for attr in attrs_elem.findall("attribute"):
                        if attr.get("name") == "type":
                            link_type = attr.text
                            break

                if link_type in road_types:
                    if cap_factor == 0.0:
                        links_elem.remove(link)
                    else:
                        orig_speed = float(link.get("freespeed", 0))
                        orig_cap   = float(link.get("capacity", 0))
                        link.set("freespeed", f"{orig_speed * speed_factor:.4f}")
                        link.set("capacity",  f"{orig_cap   * cap_factor:.4f}")
                    modified += 1

        total_modified += modified
        if cap_factor == 0.0 and link_id_target:
            pass  # already printed inside the removal block
        elif cap_factor == 0.0:
            print(f"  🚫 [{name}] speed×{speed_factor}, capacity×{cap_factor} → {modified:,} links REMOVED")
        else:
            print(f"  ✅ [{name}] speed×{speed_factor}, capacity×{cap_factor} → {modified:,} links modified")

    print(f"\nTotal links modified: {total_modified:,} / {len(all_links):,}")

    # Write output
    os.makedirs(os.path.dirname(output_network), exist_ok=True)
    with gzip.open(output_network, "wb") as f:
        tree.write(f, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    print(f"✅ New network saved at: {output_network}")
    print(f"\n👉 Remember to update config.xml to point to the new network:")
    print(f'   <param name="inputNetworkFile" value="processed/network_condition.xml.gz"/>')


def main():
    # Accept conditions file path from argument or use default
    conditions_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONDITIONS_FILE

    print("=" * 60)
    print("  Apply Traffic Conditions to MATSim Network")
    print(f"  Config: {conditions_file}")
    print(f"  (See guide: data/traffic_conditions_guide.txt)")
    print("=" * 60)

    result = load_conditions(conditions_file, project_root=_PROJECT_ROOT)
    if result is None:
        return

    input_network, output_network, conditions = result
    print(f"\nInput network : {input_network}")
    print(f"Output network: {output_network}")
    print(f"Conditions    : {len(conditions)} entries")

    apply_conditions(input_network, output_network, conditions)
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
