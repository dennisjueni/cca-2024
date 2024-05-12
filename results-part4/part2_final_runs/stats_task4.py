import os
import sys
from datetime import datetime
import numpy as np
from matplotlib.patches import Patch


total_times = {}

interval = 2

num_runs = 1

if len(sys.argv) > 1:
    BASE_DIR = sys.argv[1]
else:
    # This just takes the newest subfolder!
    main_folder_path = "./results-part4/part2"
    subfolders = [
        os.path.join(main_folder_path, f)
        for f in os.listdir(main_folder_path)
        if os.path.isdir(os.path.join(main_folder_path, f))
    ]
    subfolders.sort()
    BASE_DIR = subfolders[-1]


for i in range(num_runs):

    LOG_FILE_PATH_PARS = BASE_DIR + f"/log.txt"  # /int10_run{i+2}/log.txt

    time_format = "%Y-%m-%dT%H:%M:%SZ"
    file = open(LOG_FILE_PATH_PARS, "r")
    lines = file.read().splitlines()

    start_events = {}
    start_times = []
    completion_times = []
    durations = {}
    for line in lines:
        time = datetime.fromisoformat(line.split()[0])
        event = line.split()[1]
        name = line.split()[2]
        if name == "scheduler" or name == "memcached":
            continue

        if event == "start":
            start_events[name] = time
        elif event == "unpause":
            start_events[name] = time
        elif event == "end" or event == "pause":
            try:
                start_time = start_events[name]

                completion_time = time
                completion_times.append(completion_time)
                start_times.append(start_time)
                if name in durations.keys():
                    durations[name] += completion_time - start_time
                else:
                    durations[name] = completion_time - start_time
            except KeyError:
                print("Job {0} has not completed....".format(name))
                sys.exit(0)
        elif event == "update_cores":
            continue
        else:
            print("WARNING: UNKNOWN EVENT", event)
    for key in durations.keys():
        if i == 0:
            total_times[key] = [durations[key]]
        else:
            total_times[key].append(durations[key])

    name = "total_time"
    if i == 0:
        total_times[name] = [max(completion_times) - min(start_times)]
    else:
        total_times[name].append(max(completion_times) - min(start_times))

    file.close()


for key in total_times.keys():
    times = total_times[key]
    assert len(times) == num_runs
    times = [x.total_seconds() for x in times]
    mean = np.mean(times)
    std = np.std(times)
    print(f"{key}: mean = {mean:.2f}, std = {std:.2f}")

total_time_over_all_runs = np.sum(total_times["total_time"]).total_seconds()
violation = 0

for i in range(num_runs):
    LOG_FILE_PATH_MEMC = BASE_DIR + f"/mcperf.txt"  # /int10_run{i+2}/mcperf.txt
    mc_file = open(LOG_FILE_PATH_MEMC, "r")
    mc_file = mc_file.read()
    lines = mc_file.splitlines()
    entries = [line.split() for line in lines]
    entries = [entry for entry in entries if len(entry) == 18][1:]
    for entry in entries:
        p95 = float(entry[-6])
        if p95 > 1000:
            violation += 1


print(f"Violation rate of {violation*interval*100./total_time_over_all_runs}%")
