import sys
import os
import subprocess


# Example runs:
default_checks = [
    # 10 minutes watchdog:
    ["{scenario: watchdog, name: _none_, value: _none_}",
     "23:29:59", "1", "10"],
    # 24-hout watchdog:
    ["{scenario: watchdog, name: _none_, value: _none_}",
     "15:29:59", "24", "60", "30"],

    # Switch buttons for single light
    ["{scenario: switch, name: button.testled_button1, value: single}",
     "13:01:00", "3", "5"],
    ["{scenario: switch, name: button.testled_button2, value: double}",
     "13:01:00", "3", "5"],
    ["{scenario: switch, name: button.testled_button3, value: double}",
     "13:01:00", "3", "5"],

    # Switch buttons for list of lights
    ["{scenario: switch, name: button.testgroup_button1, value: single}",
     "13:01:00", "3", "5"],
    ["{scenario: switch, name: button.testgroup_button1, value: double}",
     "13:01:00", "3", "5"],

    # Sensors for single light
    ["{scenario: sensor, name: sensor.testled_occupancy1, value: 'on'}",
     "23:00:00", "48", "31", "30"],
    ["{scenario: sensor, name: sensor.testled_occupancy2, value: 'on'}",
     "23:00:00", "48", "31", "30"],
    ["{scenario: sensor, name: sensor.testled_occupancy3, value: 'on'}",
     "23:00:00", "48", "31", "30"],

    # Value range sensor for single
    ["{scenario: sensor, name: sensor.testled_occupancy4, value: 49}",
     "23:00:00", "48", "31", "30"],
    ["{scenario: sensor, name: sensor.testled_occupancy4, value: 50}",
     "23:00:00", "48", "31", "30"],
    ["{scenario: sensor, name: sensor.testled_occupancy4, value: 60}",
     "23:00:00", "48", "31", "30"],
    ["{scenario: sensor, name: sensor.testled_occupancy4, value: 61}",
     "23:00:00", "48", "31", "30"],

    # Sensors for list of lights
    ["{scenario: sensor, name: sensor.testgroup_occupancy, value: 'on'}",
     "23:00:00", "48", "31", "30"]
]


def run_checks(config, output_dir=None, state_output=None, checks=None, check_list=None):

    if output_dir is None or output_dir == "":
        output_stdo = True
        output_dir = ""
    else:
        output_stdo = False

    if state_output is None:
        state_output = ""

    if checks is None:
        checks = default_checks

    if check_list is None:
        check_list = range(0, len(checks))

    if output_dir != ".":
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        else:
            if not os.path.isdir(output_dir):
                raise ValueError(f"Output path {output_dir} already exists and it's not dir!")

    if not output_stdo:
        for i in check_list:
            opath = os.path.join(output_dir, ".run_{}.txt".format(i+1))
            with open(opath, "wb") as f:
                pass

    for i in check_list:
        args = [config, state_output] + checks[i]
        op = ["python", os.path.join("..", "lights_control_check.py")] + args
        if not output_stdo:
            print("Run {}: '{}'".format(i+1, " ".join(['"'+item+'"' for item in op])))
        result = subprocess.run(op, stdout=subprocess.PIPE)
        opath = os.path.join(output_dir, ".run_{}.txt".format(i+1))
        if not output_stdo:
            with open(opath, "wb") as f:
                f.write("[Run]\n{}\n\n".format(i+1).encode('utf-8'))
                f.write("[Command]\n{}\n\n".format(" ".join(['"'+item+'"' for item in op])).encode('utf-8'))
                f.write("[Result]\n".encode('utf-8'))
                f.write(result.stdout)
        else:
            print(result)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        config = sys.argv[1]
    else:
        config = os.path.join("..", "example_config", "testing", "lights_control.yaml")

    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    else:
        output_dir = ".check_run_output"

    # NOTE: sys.argv[3] selects certain test index

    if len(sys.argv) > 4:
        state_output = os.path.join(output_dir, sys.argv[4])
    else:
        state_output = os.path.join(output_dir, ".state.yaml")

    if len(sys.argv) > 3:
        check_list = [int(sys.argv[3])]
    else:
        check_list = None

    run_checks(config, output_dir, state_output, default_checks, check_list)
