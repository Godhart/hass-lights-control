import sys
import os
import subprocess

if len(sys.argv) > 1:
    config = sys.argv[1]
else:
    config = os.path.join("..", "example_config", "testing", "lights_control.yaml")

if len(sys.argv) > 2:
    output_dir = sys.argv[2]
else:
    output_dir = ".check_run_output"

# NOTE: sys.argv[3] selects certain test

if output_dir != ".":
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    else:
        if not os.path.isdir(output_dir):
            raise ValueError(f"Output path {output_dir} already exists and it's not dir!")

if len(sys.argv) > 4:
    state_output = os.path.join(output_dir, sys.argv[4])
else:
    state_output = os.path.join(output_dir, ".state.yaml")

# Example runs:
args = [
    # 10 minutes watchdog:
    [config, state_output, "{scenario: watchdog, name: _none_, value: _none_}",
     "23:29:59", "1", "10"],
    # 24-hout watchdog:
    [config, state_output, "{scenario: watchdog, name: _none_, value: _none_}",
     "15:29:59", "24", "60"],

    # Switch buttons for single light
    [config, state_output, "{scenario: switch, name: button.testled_button1, value: single}",
     "13:01:00", "3", "5"],
    [config, state_output, "{scenario: switch, name: button.testled_button2, value: double}",
     "13:01:00", "3", "5"],
    [config, state_output, "{scenario: switch, name: button.testled_button3, value: double}",
     "13:01:00", "3", "5"],

    # Switch buttons for list of lights
    [config, state_output, "{scenario: switch, name: button.testgroup_button1, value: single}",
     "13:01:00", "3", "5"],
    [config, state_output, "{scenario: switch, name: button.testgroup_button1, value: double}",
     "13:01:00", "3", "5"],

    # Sensors for single light
    [config, state_output, "{scenario: sensor, name: sensor.testled_occupancy1, value: 'on'}",
     "23:00:00", "48", "31"],
    [config, state_output, "{scenario: sensor, name: sensor.testled_occupancy2, value: 'on'}",
     "23:00:00", "48", "31"],
    [config, state_output, "{scenario: sensor, name: sensor.testled_occupancy3, value: 'on'}",
     "23:00:00", "48", "31"],

    # Value range sensor for single
    [config, state_output, "{scenario: sensor, name: sensor.testled_occupancy4, value: 49}",
     "23:00:00", "48", "31"],
    [config, state_output, "{scenario: sensor, name: sensor.testled_occupancy4, value: 50}",
     "23:00:00", "48", "31"],
    [config, state_output, "{scenario: sensor, name: sensor.testled_occupancy4, value: 60}",
     "23:00:00", "48", "31"],
    [config, state_output, "{scenario: sensor, name: sensor.testled_occupancy4, value: 61}",
     "23:00:00", "48", "31"],

    # Sensors for list of lights
    [config, state_output, "{scenario: sensor, name: sensor.testgroup_occupancy, value: 'on'}",
     "23:00:00", "48", "31"]
]

if len(sys.argv) > 3:
    ops = range(int(sys.argv[3])-1, int(sys.argv[3]))
else:
    ops = range(0, len(args))

for i in ops:
    opath = os.path.join(output_dir, ".run_{}.txt".format(i+1))
    with open(opath, "wb") as f:
        pass

for i in ops:
    op = ["python.exe", os.path.join("..", "lights_control_check.py")] + args[i]
    print("Run {}: '{}'".format(i+1, " ".join(['"'+item+'"' for item in op])))
    result = subprocess.run(op, stdout=subprocess.PIPE)
    opath = os.path.join(output_dir, ".run_{}.txt".format(i+1))
    with open(opath, "wb") as f:
        f.write("[Run]\n{}\n\n".format(i+1).encode('utf-8'))
        f.write("[Command]\n{}\n\n".format(" ".join(['"'+item+'"' for item in op])).encode('utf-8'))
        f.write("[Result]\n".encode('utf-8'))
        f.write(result.stdout)
