import sys
from typing import Dict, List, Tuple
from matplotlib import pyplot as plt
from matplotlib.patches import Patch
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
    "memcached": "#CC00AA",
    "p95 latency": "C0",
}


def main():

    runs = ["run1", "run2", "run3"]

    calculate_execution_time(runs)

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

    benchmark_runs: List[Tuple[datetime, datetime, str, str, str, str]] = (
        []
    )  # (start, finish, name, machine, color, cores)
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

    legend_elements = [Patch(facecolor=colors[i], label=i) for i in colors]

    fig = plt.figure(figsize=(20, 9), dpi=600)
    ax = plt.subplot(111)
    ax.xaxis.grid(True, which="both")
    ax.yaxis.grid(True, which="both")
    ax.set_axisbelow(True)
    # ax.yaxis.grid(True, which='ma')
    START = min(start_times)
    HEIGHT = 100
    HEIGHT_NO_OFFSET = 80
    MARGIN = 200
    NODE_A_START = MARGIN + 1000
    ax.axhline(y=NODE_A_START - MARGIN / 2, color="k", linestyle="-")

    NODE_B_START = NODE_A_START + 2 * HEIGHT + MARGIN
    ax.axhline(y=NODE_B_START - MARGIN / 2, color="k", linestyle="-")
    NODE_C_START = NODE_B_START + 4 * HEIGHT + MARGIN
    ax.axhline(y=NODE_C_START - MARGIN / 2, color="k", linestyle="-")

    NODE_C_END = NODE_C_START + 8 * HEIGHT + MARGIN / 2
    ax.axhline(y=NODE_C_END - 4, color="k", linestyle="-")

    for run in benchmark_runs:
        if run[3].startswith("node-a"):
            offset = NODE_A_START
        elif run[3].startswith("node-b"):
            offset = NODE_B_START
        elif run[3].startswith("node-c"):
            offset = NODE_C_START
        else:
            print("Wrong machine", run[3])
            sys.exit(0)
        for core in run[5]:
            ax.barh(
                int(core) * HEIGHT + offset + 10,
                (run[1] - run[0]).total_seconds(),
                left=(run[0] - min(start_times)).total_seconds(),
                color=run[4],
                height=HEIGHT_NO_OFFSET,
                align="edge",
            )
    ax.barh(NODE_A_START + 10, MAX_LEN, left=0, color=colors["memcached"], height=HEIGHT_NO_OFFSET, align="edge")

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
        ax.bar((start + end) / 2, float(p95), width=10, color=colors["p95 latency"])

    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.1, box.width, box.height * 0.9])  # type: ignore

    # Put a legend below current axis
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.08),
        fancybox=True,
        shadow=True,
        ncol=5,
        handles=legend_elements,
        prop={"size": 16},
    )
    # plt.legend(handles=legend_elements)
    # axs[3].set_ylim([0,1000])
    plt.xticks(np.arange(0, MAX_LEN + 1, step=10), minor=False)
    plt.xlim(0, MAX_LEN)
    yticks: List[float] = [0, 500, 1000]
    ylabels = [0, 0.5, 1]
    for i in range(2):
        yticks.append(NODE_A_START + (2 * i + 1) * HEIGHT / 2)
        ylabels.append(i)
    for i in range(4):
        yticks.append(NODE_B_START + (2 * i + 1) * HEIGHT / 2)
        ylabels.append(i)
    for i in range(8):
        yticks.append(NODE_C_START + (2 * i + 1) * HEIGHT / 2)
        ylabels.append(i)
    plt.yticks(yticks, labels=ylabels)

    plt.title(f"Memcached p95 Latency and PARSEC Schedule for Run 3", fontdict={"fontsize": 24}, pad=15)
    plt.xlabel("time since first job started [s]", fontdict={"fontsize": 18})
    plt.ylim(0, NODE_C_END)

    plt.savefig(fname=f"results-part3/final_runs/{current_run}_plot.pdf")


if __name__ == "__main__":
    main()
