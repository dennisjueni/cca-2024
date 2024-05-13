import sys
from typing import Dict, List, Tuple
from matplotlib import pyplot as plt
import numpy as np
import json
from datetime import datetime, timedelta


time_format = "%Y-%m-%dT%H:%M:%SZ"
colors = {
    "parsec-blackscholes": "#CCA000",
    "parsec-canneal": "#CCCCAA",
    "parsec-dedup": "#CCACCA",
    "parsec-ferret": "#AACCCA",
    "parsec-freqmine": "#0CCA00",
    "parsec-radix": "#00CCA0",
    "parsec-vips": "#CC0A00",
    "memcached": "#888888",
}
p95_color = "#6A0DAD"

labels = {
    "parsec-blackscholes": "Blackscholes",
    "parsec-canneal": "Canneal",
    "parsec-dedup": "Dedup",
    "parsec-ferret": "Ferret",
    "parsec-freqmine": "Freqmine",
    "parsec-radix": "Radix",
    "parsec-vips": "Vips",
    "memcached": "Memcached",
}

def plot():

    runs = ["run1", "run2", "run3"]

    for run in runs:
        generate_plots(run)


def calculate_execution_time(runs: List[str]):

    total_time_name = "total_time"
    total_exec_time: Dict[str, List[timedelta]] = {}

    for run in runs:

        results_file = open(f"results-part3/final_runs/{run}/results.json", "r")
        json_file = json.load(results_file)

        start_times = []
        completion_times = []

        for item in json_file["items"]:
            name = item["status"]["containerStatuses"][0]["name"]
            if str(name) == "memcached":
                continue
            try:
                start_time = datetime.strptime(
                    item["status"]["containerStatuses"][0]["state"]["terminated"]["startedAt"], time_format
                )
                completion_time = datetime.strptime(
                    item["status"]["containerStatuses"][0]["state"]["terminated"]["finishedAt"], time_format
                )

                if name in total_exec_time.keys():
                    total_exec_time[name].append(completion_time - start_time)
                else:
                    total_exec_time[name] = [completion_time - start_time]

                start_times.append(start_time)
                completion_times.append(completion_time)
 
            except KeyError:
                print("Job {0} has not completed....".format(name))
                sys.exit(0)

        if total_time_name in total_exec_time.keys():
            total_exec_time[total_time_name].append(max(completion_times) - min(start_times))
        else:
            total_exec_time[total_time_name] = [max(completion_times) - min(start_times)]

        results_file.close()

    for key, values in total_exec_time.items():

        if len(values) != 3:
            print("Somehow not 3 runs were completed for job: ", key)

        exec_time_in_sec = [x.total_seconds() for x in values]
        mean = np.mean(exec_time_in_sec)
        std = np.std(exec_time_in_sec)

        if key == total_time_name:
            print(f"total time & {mean:.2f} & {std:.2f} \\\\  \\hline")
        else:
            print(f"\\coloredcell{{{key.removeprefix("parsec-")}}} & {mean:.2f} & {std:.2f} \\\\  \\hline")


def generate_plots(current_run: str):

    benchmark_runs: List[Tuple[datetime, datetime, str, str, str, str]] = []  # (start, finish, name, machine, color, cores)
    results_file = open(f"results-part3/final_runs/{current_run}/results.json", "r")
    json_file = json.load(results_file)
    start_times = []
    completion_times = []
    total_time_name = "total_time"
    total_exec_time: Dict[str, List[timedelta]] = {}

    for item in json_file["items"]:
        name = item["status"]["containerStatuses"][0]["name"]
        command = item["spec"]["containers"][0]["args"][1]
        command = command.rsplit(" ./")[0]
        command = command.rsplit("-c ")[1]
        cores = command.rsplit(",")
        machine = item["spec"]["nodeSelector"]["cca-project-nodetype"]
        if str(name) != "memcached":
            try:
                start_time = datetime.strptime(
                    item["status"]["containerStatuses"][0]["state"]["terminated"]["startedAt"], time_format
                )
                completion_time = datetime.strptime(
                    item["status"]["containerStatuses"][0]["state"]["terminated"]["finishedAt"], time_format
                )

                if name in total_exec_time.keys():
                    total_exec_time[name].append(completion_time - start_time)
                else:
                    total_exec_time[name] = [completion_time - start_time]

                start_times.append(start_time)
                completion_times.append(completion_time)
                benchmark_runs.append((start_time, completion_time, name, machine, colors[name], cores))

            except KeyError:
                print("Job {0} has not completed....".format(name))
                sys.exit(0)

    if total_time_name in total_exec_time.keys():
        total_exec_time[total_time_name].append(max(completion_times) - min(start_times))
    else:
        total_exec_time[total_time_name] = [max(completion_times) - min(start_times)]

    results_file.close()

    MAX_LEN = max((max(completion_times) - min(start_times)).total_seconds(), 180)

    fig = plt.figure(figsize=(20, 9), dpi=600)
    ax = plt.subplot(111)
    # Make sure we have a grid (only on major yticks) & assure the grid is drawn below all bars
    ax.xaxis.grid(True, which="both")
    ax.yaxis.grid(True, which="major")
    ax.set_axisbelow(True)

    START = min(start_times)
    HEIGHT = 100
    HEIGHT_NO_OFFSET = 90
    MAIN_MARGIN = 200
    MARGIN = 50

    NODE_C_START = MAIN_MARGIN + 1000
    ax.axhline(y=NODE_C_START - MAIN_MARGIN / 2 + 10, color="k", linestyle="-", linewidth=1.5)

    NODE_B_START = NODE_C_START + 8 * HEIGHT + MARGIN
    ax.axhline(y=NODE_B_START - MARGIN / 2, color="k", linestyle="-", linewidth= 0.75)

    NODE_A_START = NODE_B_START + 4 * HEIGHT + MARGIN
    ax.axhline(y=NODE_A_START - MARGIN / 2, color="k", linestyle="-", linewidth = 0.75)

    NODE_A_END = NODE_A_START + 2 * HEIGHT + MARGIN / 2

    for run in benchmark_runs:
        if run[3].startswith("node-a"):
            offset = NODE_A_START
            num_cores = 2
        elif run[3].startswith("node-b"):
            offset = NODE_B_START
            num_cores = 4
        elif run[3].startswith("node-c"):
            offset = NODE_C_START
            num_cores = 8
        else:
            print("Wrong machine", run[3])
            sys.exit(0)
        for core in run[5]:
            name = run[2].removeprefix("parsec-").capitalize()
            y_val = (num_cores - int(core) - 1) * HEIGHT + offset + 10
            left_x = (run[0] - min(start_times)).total_seconds()
            width = (run[1] - run[0]).total_seconds()

            ax.barh(
                y_val,
                width,
                left=left_x,
                color=run[4],
                height=HEIGHT_NO_OFFSET,
                align="edge",
            )
            ax.text(left_x + width / 2, y_val + 10, f'{name}', ha='center', va='bottom', color='white', fontweight='bold')

    ax.barh(NODE_A_START + HEIGHT + 10, MAX_LEN, left=0, color=colors["memcached"], height=HEIGHT_NO_OFFSET, align="edge")
    ax.text(0 + MAX_LEN / 2, NODE_A_START + HEIGHT + 20, f'Memcached', ha='center', va='bottom', color='white', fontweight='bold')


    mc_file = open(f"results-part3/final_runs/{current_run}/mcperf.txt", "r")
    mc_file = mc_file.read()
    lines = mc_file.splitlines()
    entries = [line.split() for line in lines]
    entries = [entry for entry in entries if len(entry) == 20][1:]

    for entry in entries:
        end = datetime.utcfromtimestamp(int(entry[-1]) / 1000)
        start = datetime.utcfromtimestamp(int(entry[-2]) / 1000)

        end = (end - START).total_seconds()
        start = (start - START).total_seconds()
        p95 = entry[-8]
        ax.bar((start + end) / 2, float(p95), width=10, color=p95_color, edgecolor='black', linewidth=1)

    ax.axhline(y=1000, color="black", linestyle="--", xmax=0.485)
    ax.axhline(y=1000, color="black", linestyle="--", xmin=0.515)
    ax.text(MAX_LEN / 2, 998, 'SLO', va='center', ha='center', color='black', fontsize=12)


    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.1, box.width, box.height * 0.9])  # type: ignore

    plt.text(-20, 500 - MARGIN/4, 'P95 latency (ms)')
    plt.text(-20, (NODE_C_START + NODE_B_START - MARGIN) / 2, 'Node C (8 cores)')
    plt.text(-20, (NODE_B_START + NODE_A_START - MARGIN) / 2, 'Node B (4 cores)')
    plt.text(-20, (NODE_A_START + NODE_A_END - MARGIN/2) / 2, 'Node A (2 cores)')


    plt.xticks(np.arange(0, MAX_LEN + 1, step=10), minor=False)
    plt.xlim(0, MAX_LEN)

    yticks: List[float] = [0, 250, 500, 750, 1000]
    ylabels = [0, 0.25, 0.5, 0.75, 1]
    ax.set_yticks(yticks, labels=ylabels, minor=False)

    yticks = []
    ylabels = []
    for i in range(2):
        yticks.append(NODE_A_START + (2 * i + 1) * HEIGHT / 2)
        ylabels.append(2-i-1)
    for i in range(4):
        yticks.append(NODE_B_START + (2 * i + 1) * HEIGHT / 2)
        ylabels.append(4-i-1)
    for i in range(8):
        yticks.append(NODE_C_START + (2 * i + 1) * HEIGHT / 2)
        ylabels.append(8-i-1)

    ax.set_yticks(yticks, labels=ylabels, minor=True)

    plt.title(f"P95 Latency of Memcached & Benchmark Schedule", fontdict={"fontsize": 20}, pad=15)
    plt.xlabel("Time since first PARSEC benchmark started (sec)", fontdict={"fontsize": 15})
    plt.ylim(0, NODE_A_END)

    plt.savefig(fname=f"results-part3/final_runs/{current_run}_plot.pdf")
