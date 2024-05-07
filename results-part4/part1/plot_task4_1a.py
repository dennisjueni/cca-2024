import sys
import matplotlib.pyplot as plt
import numpy as np

MEASURE_DIR = "./results-part4/part1/2024-05-07-21-15/"
QPS_MIN = 0
QPS_MAX = 130_000
fig = plt.figure(figsize=(16, 9))

labels = {0: "1 core, 1 thread", 1: "1 core, 2 threads", 2: "2 cores, 1 thread", 3: "2 cores, 2 threads"}

suffix = {0: "1C_1T", 1: "1C_2T", 2: "2C_1T", 3: "2C_2T"}

for i in range(4):
    qps = []
    p95 = []
    xs = []
    ys = []
    target = []
    xerr = []
    yerr = []
    groups_y = {}
    groups_x = {}
    for j in range(3):
        file_path = MEASURE_DIR + f"{suffix[i]}/run_{j}/mcperf.txt"
        file = open(file_path, "r")
        lines = file.read().splitlines()
        lines = [line.split() for line in lines]
        lines = [line for line in lines if len(line) == 20][1:]

        qps = qps + [float(line[-4]) for line in lines]
        target = target + [float(line[-3]) for line in lines]
        p95 = p95 + [float(line[-8]) / 1000 for line in lines]

    for j in range(len(qps)):
        key = target[j]
        if key in groups_x.keys():
            groups_y[key].append(p95[j])
            groups_x[key].append(qps[j])
        else:
            groups_y[key] = [p95[j]]
            groups_x[key] = [qps[j]]
    for key in groups_x.keys():
        assert len(groups_x[key]) == 3
        xs.append(np.mean(groups_x[key]))
        ys.append(np.mean(groups_y[key]))
        xerr.append(np.std(groups_x[key]))
        yerr.append(np.std(groups_y[key]))

    xs, ys, xerr, yerr = zip(*list(sorted(list(zip(xs, ys, xerr, yerr)))))
    plt.errorbar(xs, ys, xerr=xerr, yerr=yerr, label=labels[i], capsize=3)
plt.xlabel("QPS")
plt.ylabel("p95 latency [ms]")
plt.hlines(1, xmin=QPS_MIN, xmax=QPS_MAX, color="k", linestyles="--")
plt.xlim(QPS_MIN, QPS_MAX)
plt.legend()

plt.title("P95 latency vs. QPS for Different Number of Threads and Cores")
plt.tight_layout()

plt.savefig(fname=f"test.pdf")
