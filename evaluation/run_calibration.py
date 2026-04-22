import subprocess

subprocess.run([
    "python",
    "evaluation/grouped_calibration.py",
    "--network", "output/output_network.xml.gz",
    "--config", "evaluation/network_paths/config_corridors_from_network.json",
    "--eval", "evaluation/results/evaluation_table.csv",
    "--output", "output/output_network_calibrated_v1.xml.gz"
])