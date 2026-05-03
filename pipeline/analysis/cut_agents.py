"""
fix_plan_home_end.py — แก้ไข agent plan ที่ไม่จบด้วย home
โดยตัด activity และ leg ส่วนท้ายออกจนกว่า activity สุดท้ายจะเป็น home

Usage:
    python pipeline/fix_plan_home_end.py <input_plan.xml> <output_plan.xml>
    python pipeline/fix_plan_home_end.py <input_plan.xml> <output_plan.xml> --dry-run
"""

import sys
import os
import argparse
import gzip
from lxml import etree
from tqdm import tqdm


def fix_plan(plan_el):
    """
    ตัด leg และ activity ท้ายออกจนกว่า activity สุดท้ายจะเป็น home
    คืนค่า True ถ้าแก้ไข, False ถ้าไม่ต้องแก้ หรือ None ถ้าแก้ไม่ได้
    """
    children = list(plan_el)
    # แยก activity กับ leg
    acts = [c for c in children if c.tag == "activity"]

    if not acts:
        return None  # ไม่มี activity เลย

    last_act = acts[-1]
    if last_act.get("type", "") == "home":
        return False  # ดีอยู่แล้ว ไม่ต้องแก้

    # หา home ล่าสุดที่อยู่ใน plan
    home_indices = [i for i, c in enumerate(children)
                    if c.tag == "activity" and c.get("type", "") == "home"]

    if not home_indices:
        return None  # ไม่มี home ใน plan เลย แก้ไม่ได้

    last_home_idx = home_indices[-1]

    # ลบ element ทุกอันหลัง last home
    to_remove = children[last_home_idx + 1:]
    for el in to_remove:
        plan_el.remove(el)

    return True


def process_file(input_path: str, output_path: str, dry_run: bool = False):
    print(f"\n{'='*55}")
    print(f"  Fix Plan Home End")
    print(f"{'='*55}")
    print(f"  Input  : {input_path}")
    print(f"  Output : {output_path}")
    print(f"  Mode   : {'DRY RUN (ไม่บันทึก)' if dry_run else 'WRITE'}")
    print(f"{'='*55}\n")

    # โหลดไฟล์
    print("Parsing XML...", end=" ", flush=True)
    is_gz = input_path.endswith(".gz")
    if is_gz:
        with gzip.open(input_path, "rb") as f:
            tree = etree.parse(f)
    else:
        tree = etree.parse(input_path)
    print("done.\n")

    root = tree.getroot()
    persons = root.findall(".//person")

    fixed = 0
    skipped_no_home = 0
    already_ok = 0

    # ต้องเก็บ parent ของแต่ละ person ไว้เพื่อลบออก
    population_el = root.find(".//population") or root

    persons_to_remove = []

    for person in tqdm(persons, desc="Processing agents", unit="agent"):
        plans = person.findall("plan")

        # เลือก selected plan
        selected = next(
            (p for p in plans if p.get("selected", "no") == "yes"),
            plans[0] if plans else None
        )

        if selected is None:
            persons_to_remove.append(person)
            skipped_no_home += 1
            continue

        result = fix_plan(selected)

        if result is True:
            fixed += 1
        elif result is False:
            already_ok += 1
        elif result is None:
            # ไม่มี home ใน plan เลย → ลบ agent ออก
            persons_to_remove.append(person)
            skipped_no_home += 1

    # ลบ agent ที่ไม่มี home ออกจาก XML
    for person in persons_to_remove:
        person.getparent().remove(person)

    # สรุป
    remaining = len(persons) - len(persons_to_remove)
    print(f"\n┌─ Result {'─'*44}┐")
    print(f"│  Total agents (input)   : {len(persons):>10,}            │")
    print(f"│  Already end with home  : {already_ok:>10,}            │")
    print(f"│  Fixed (trimmed)        : {fixed:>10,}            │")
    print(f"│  Removed (no home act)  : {len(persons_to_remove):>10,}            │")
    print(f"│  Remaining agents       : {remaining:>10,}            │")
    print(f"└{'─'*53}┘\n")

    if skipped_no_home > 0:
        print(f"🗑️  ลบ {skipped_no_home:,} agents ที่ไม่มี home activity ออกแล้ว\n")

    # บันทึก
    if not dry_run:
        if fixed == 0 and skipped_no_home == 0:
            print("✅ ไม่มีอะไรต้องแก้ ไม่บันทึกไฟล์ใหม่")
            return

        print(f"Writing output...", end=" ", flush=True)
        doctype = '<!DOCTYPE population SYSTEM "http://www.matsim.org/files/dtd/population_v6.dtd">'
        tree = etree.ElementTree(root)
        if output_path.endswith(".gz"):
            with gzip.open(output_path, "wb") as f:
                tree.write(f, pretty_print=True, xml_declaration=True,
                           encoding="UTF-8", doctype=doctype)
        else:
            tree.write(output_path, pretty_print=True, xml_declaration=True,
                       encoding="UTF-8", doctype=doctype)
        print("done.")
        print(f"✅ บันทึกแล้วที่ {output_path}\n")
    else:
        print("ℹ️  Dry run — ไม่มีการบันทึกไฟล์\n")


def main():
    parser = argparse.ArgumentParser(
        description="Fix MATSim plans that do not end with home activity")
    parser.add_argument("input",  help="Input plan XML or XML.gz")
    parser.add_argument("output", help="Output plan XML or XML.gz")
    parser.add_argument("--dry-run", action="store_true",
                        help="แสดงผลอย่างเดียว ไม่บันทึกไฟล์")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: ไม่พบไฟล์ {args.input}")
        sys.exit(1)

    process_file(args.input, args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
