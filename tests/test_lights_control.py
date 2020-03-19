import pytest
import os
import sys
import subprocess
import re
import difflib


def setup_module(module):
    #init_something()
    os.chdir("tests")


def teardown_module(module):
    #teardown_something()
    os.chdir("..")


def test_pass():
    assert True


def parse_test_data(filepath):
    command = None
    data = None
    next_command = False
    with open(filepath, "r") as f:
        for line in f:
            if data is None and command is None and line.strip() == "[Command]":
                next_command = True
                continue
            if next_command:
                next_command = False
                command = re.findall('"([^"]*)"', line)
                command = [c.replace("\\", os.path.sep) for c in command]
                # command = [os.path.normcase(os.path.normpath(c)) for c in command]
                continue
            if command is not None and line.strip() == "[Result]":
                data = ""
                continue
            if data is not None:
                data += line
    return command, data


def test_smoke():
    tests_count = 0
    failed_runs = []
    print("Running smoke test from {}\n".format(os.getcwd()), file=sys.stderr)
    try:
        test_data_dir = os.path.join(".", "smoke_test_data")
        for curdir, subs, files in os.walk(test_data_dir):
            # print("{}\n{}\n{}\n".format(curdir, subs, files), file=sys.stderr)
            for filename in files:
                print(f"  {filename}:", file=sys.stderr)
                if filename[-4:] != ".txt":
                    continue
                if "skip" in curdir:
                    continue
                op, expected = parse_test_data(os.path.join(curdir, filename))
                if op is None or expected is None:
                    print("    FAILED to parse test data\n", file=sys.stderr)
                    failed_runs.append(filename)
                    continue
                print("Running {}".format(" ".join(['"' + c + '"' for c in op])), file=sys.stderr)
                result = subprocess.run(op, stdout=subprocess.PIPE)
                output = result.stdout.decode('utf-8').replace("\r\n", "\n").replace("\n\r", "\n")
                if output != expected:
                    print("    FAILED as result is not same as expected\n", file=sys.stderr)
                    for i, s in enumerate(difflib.unified_diff(expected.split('\n'), output.split('\n'),
                                                               fromfile='expected', tofile='result')):
                        print(f"{i}:{s}", file=sys.stderr)
                    if __name__ == "__main__":
                        with open(".pytest_error_dump", "w") as f:
                            f.write(output)
                    failed_runs.append(filename)
                else:
                    print("    SUCCESS\n", file=sys.stderr)
                tests_count += 1
    except Exception as e:
        print("    FAILED due to exception {}\n".format(e), file=sys.stderr)
        assert False

    assert tests_count > 0
    if len(failed_runs) > 0:
        assert "Failed runs: " + ", ".join(sorted(failed_runs)) == ""

# def test_fail():
#    assert False


if __name__ == "__main__":
    test_smoke()
