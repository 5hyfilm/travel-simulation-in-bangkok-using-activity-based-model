from lxml import etree
import gzip

toll_links = []

with gzip.open("data/processed/network.xml.gz", "rb") as f:
    for event, elem in etree.iterparse(f, tag="link"):
        cap = int(float(elem.get("capacity", 0)))
        freespeed = float(elem.get("freespeed", 0))
        if cap >= 2000 and freespeed * 3.6 >= 80:
            toll_links.append(elem.get("id"))
        elem.clear()

print(f"Toll links found: {len(toll_links):,}")

# เขียน toll_links.xml (format ถูกต้อง)
with open("preprocess/output/toll_links.xml", "w") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<!DOCTYPE roadpricing SYSTEM "http://www.matsim.org/files/dtd/roadpricing_v1.dtd">\n')
    f.write('<roadpricing type="distance" name="Bangkok Expressway Toll">\n')
    f.write('    <description>Bangkok motorway and expressway toll - 2.5 THB/km</description>\n')
    f.write('    <links>\n')
    for link_id in toll_links:
        f.write(f'        <link id="{link_id}"/>\n')
    f.write('    </links>\n')
    f.write('    <cost start_time="00:00:00" end_time="30:00:00" amount="0.0025"/>\n')
    f.write('</roadpricing>\n')

print("Saved toll_links.xml")