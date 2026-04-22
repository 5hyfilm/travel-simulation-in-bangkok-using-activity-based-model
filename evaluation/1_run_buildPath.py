import subprocess

subprocess.run([
    "python",
    "evaluation/build_paths_from_network.py",
    "--network", "output/output_network.xml.gz",
    "--corridors", "evaluation/corridors_for_network.json",
    "--outdir", "evaluation/network_paths",
    "--weight", "time"
])

#python build_paths_from_network.py \
#  --network ../output/output_network.xml.gz \
#  --corridors corridors_for_network.json \
#  --outdir network_paths \
#  --weight time