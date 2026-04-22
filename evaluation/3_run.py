import subprocess

subprocess.run([
    "python",
    "evaluation/matsim_google_evaluation_pipeline.py",
    "--config", "evaluation/config.json",
    "--network", "output/output_network.xml.gz",
    "--events", "output/output_events.xml.gz",
    "--outdir", "evaluation/results"
])