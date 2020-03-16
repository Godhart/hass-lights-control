import sys
import os
import subprocess

if len(sys.argv) > 1:
    config = sys.argv[1]
else:
    config = os.path.join("..", "example_config", "lights_control.yaml")

if len(sys.argv) > 2:
    output_dir = sys.argv[2]
else:
    output_dir = os.path.join(".", ".1day_wd")

op = ["python.exe", "lights_control_check_run.py", config, output_dir, "2"]
result = subprocess.run(op)
