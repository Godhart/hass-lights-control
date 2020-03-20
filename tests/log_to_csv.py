from test_lights_control import parse_test_data
import os
import sys
import re
import copy
import subprocess
from datetime import datetime


def load_data(path, check_extension=True):
    print(f"  {path}:", file=sys.stderr)
    if check_extension and path[-4:] != ".txt":
        return None
    if any("skip" in p for p in os.path.split(path)[:-1]):
        return None
    op, data = parse_test_data(path)
    if data is None:
        return None
    data = data.split("\n")
    return data


def _seconds(datetime_str):
    datetime_str = datetime_str[:-3] + datetime_str[-2:]    # Drop : in timezone spec
    return datetime.timestamp(datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S%z"))


def parse_data(lines):
    result = {}
    entities = []
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if line.strip() == "LightsControl component just inited":
            line = lines[i]
            i += 1
            t = _seconds(line)
            result[t] = {"datetime": line}
            continue
        m = re.search(r"(\w+\.\w+) were turned (ON|OFF)(?: to brightness (\d+))?"
                      r" at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\+\d{2}:?\d{2})", line)
        if m is None:
            continue
        entity, state, brightness, datetime_str = m.groups()
        state = state == "ON"
        if state and brightness is None:
            brightness = 255
        if not state and brightness is None:
            brightness = 0
        t = _seconds(datetime_str)
        if t not in result:
            result[t] = {"datetime": datetime_str}
        if entity not in result[t]:
            result[t][entity] = brightness
        if entity not in entities:
            entities.append(entity)
    return result, entities


def process_data(data, entities):
    events = sorted(data.keys())
    for e in entities:
        if e not in data[events[0]]:
            data[events[0]][e] = 0
    for i in range(1, len(events)):
        t = events[i]
        data[t - 0.5] = copy.deepcopy(data[events[i-1]])
        data[t - 0.5]["datetime"] = ""
        for e in entities:
            if e not in data[t]:
                data[t][e] = data[events[i-1]][e]


def to_csv(data, path, separator):
    with open(path, "w") as f:
        events = sorted(data.keys())
        entities = sorted(data[events[0]].keys())
        del entities[entities.index('datetime')]
        line_data = ['caption', 'seconds'] + entities
        f.write('// "python" "'+os.path.split(sys.argv[0])[-1]+'" {}\n'.format(
            " ".join(['"' + arg + '"' for arg in sys.argv[1:]])))
        f.write("{}\n".format((separator+" ").join(line_data)))
        if separator == ';':
            pt = ','
        else:
            pt = '.'
        for ev in events:
            line_data = [data[ev]['datetime'], str(ev).replace('.', pt)] + \
                        [str(data[ev][e]).replace('.', pt) for e in entities]
            line_data = [l.replace(separator, '`') for l in line_data]
            f.write("{}\n".format((separator+" ").join(line_data)))


def process_file(path, check_extension=True):
    data = load_data(path, check_extension=check_extension)
    data, entities = parse_data(data)
    process_data(data, entities)
    to_csv(data, path[:-4]+".csv", ";")


def log_to_csv(path):
    if path[-1] == '*':
        path = path[:-1]
        walk = True
    else:
        walk = False

    if not walk:
        process_file(path, check_extension=False)
        return

    for curdir, subs, files in os.walk(path):
        for filename in files:
            if filename[-4:] != ".txt":
                continue
            try:
                # process_file(os.path.join(curdir, filename))
                subprocess.run(["python", sys.argv[0], os.path.join(curdir, filename)])
            except Exception as e:
                print(f"  Failed due to exception:\n    {e}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = ".*"

    log_to_csv(path)
