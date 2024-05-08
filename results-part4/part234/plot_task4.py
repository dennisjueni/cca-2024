import json
import sys
from datetime import datetime
import pandas as pd
from matplotlib.patches import Patch
from datetime import timedelta
import numpy as np

LOG_FILE = "./results-part4/first_result/log.txt"
P95_FILE = "./results-part4/first_result/mcperf.txt"

time_format = "%Y-%m-%dT%H:%M:%S.%Z"
file = open(LOG_FILE, "r")
lines = file.read().splitlines()
MAX_LEN = 1000
runs = []  # (start, finish, name, machine, color, cores)
# df = pd.DataFrame([], columns=['start', 'finish', 'name', 'machine'])
# print(df)

c_dict = {
    "parsec-blackscholes": "#CCA000",
    "parsec-canneal": "#CCCCAA",
    "parsec-dedup": "#CCACCA",
    "parsec-ferret": "#AACCCA",
    "parsec-freqmine": "#0CCA00",
    "parsec-radix": "#00CCA0",
    "parsec-vips": "#CC0A00",
    "memcached": "#f06eee",
    "p95 latency": "royalblue",
    "QPS": "orange",
}
start_events = {}
start_times = []
completion_times = []
runs = []
durations = {}
for line in lines:
    time = datetime.fromisoformat(line.split()[0])
    event = line.split()[1]
    name = line.split()[2]
    if name == "scheduler":
        continue

    if event == "start":
        print(line.split())
        cores = line.split()[3][1:-1].split(",")
        start_events[name] = time, cores

        print(time, name, cores)

    elif event == "unpause":
        prev_time, cores = start_events[name]
        start_events[name] = time, cores
    elif event == "end" or event == "pause":
        try:
            start_time, cores = start_events[name]

            completion_time = time
            print(f"Job time {name}: ", completion_time - start_time, start_time)
            completion_times.append(completion_time)
            start_times.append(start_time)
            if name != "memcached":
                name = "parsec-" + name
            runs.append((start_time, completion_time, name, "node-a", c_dict[name], cores))
        except KeyError:
            print("Job {0} has not completed....".format(name))
            sys.exit(0)
    elif event == "update_cores":
        try:
            start_time, cores = start_events[name]
            completion_time = time
            print(f"Job time {name}: ", completion_time - start_time, start_time)
            completion_times.append(completion_time)
            start_times.append(start_time)
            if name != "memcached":
                c_name = "parsec-" + name
            else:
                c_name = name
            runs.append((start_time, completion_time, c_name, "node-a", c_dict[c_name], cores))
        except KeyError:
            print("Job {0} has not completed....".format(name))
            sys.exit(0)
        cores = line.split()[3][1:-1].split(",")
        start_events[name] = time, cores
    else:
        print("WARNING: UNKNOWN EVENT", event)


MAX_LEN = (max(completion_times) - min(start_times)).total_seconds()
print(MAX_LEN)
import matplotlib.pyplot as plt

legend_elements = [Patch(facecolor=c_dict[i], label=i) for i in c_dict]

# fig = plt.figure(figsize=(16,9))

# axs[0].yaxis.grid(True, which='ma')
fig, ax1 = plt.subplots(figsize=(20, 9))
START = min(start_times)

mc_file = open(P95_FILE, "r")
mc_file = mc_file.read()
lines = mc_file.splitlines()
memcache_start = [entry for entry in lines if entry.startswith("Timestamp start")]
assert len(memcache_start) == 1
memcache_start = datetime.utcfromtimestamp(int(memcache_start[0].split()[-1]) / 1000)

memcache_end = [entry for entry in lines if entry.startswith("Timestamp end")]
assert len(memcache_end) == 1
memcache_end = datetime.utcfromtimestamp(int(memcache_end[0].split()[-1]) / 1000)

memcache_delta = timedelta(seconds=10)

entries = [line.split() for line in lines]
entries = [entry for entry in entries if len(entry) == 18][1:]

count = 0
max_p95 = 2000
max_q = 130_000
ax2 = ax1.twinx()
xs = []
qs = []
ps = []
for entry in entries:
    end = memcache_start + (count + 1) * memcache_delta
    start = memcache_start + (count) * memcache_delta
    count += 1

    end = (end - START).total_seconds()
    start = (start - START).total_seconds()
    p95 = entry[-6]
    qps = float(entry[-2])

    xs.append(start)
    xs.append(end)
    ps.append(float(p95))
    ps.append(float(p95))
    qs.append(float(qps))
    qs.append(float(qps))

    # max_p95 = max(float(p95), max_p95)
    # max_q = max(float(qps), max_q)
    target = entry[-1]
ax1.step(xs, ps, color="royalblue")
ax2.step(xs, qs, color="orange")
# ax1.bar((start+end)/2, float(p95), width=memcache_delta.total_seconds(), color='royalblue')
# ax2.bar((start+end)/2, float(qps), width=memcache_delta.total_seconds(), color='royalblue')
# axs[2].bar((start+end)/2, float(target), width=memcache_delta.total_seconds(), color='royalblue')


HEIGHT = 100
HEIGHT_NO_OFFSET = 80
MARGIN = 100
NODE_A_START = MARGIN + max_p95

NODE_C_END = NODE_A_START + 4 * HEIGHT + MARGIN / 2

ax1.xaxis.grid(True, which="both")
ax1.yaxis.grid(True, which="both")
ax1.set_axisbelow(True)
ax1.axhline(y=NODE_A_START - MARGIN / 2, color="k", linestyle="--")
for run in runs:
    if run[3].startswith("node-a"):
        offset = NODE_A_START
    else:
        print("Wrong machine", run[3])
        sys.exit(1)
    # print(run)
    for core in run[5]:
        ax1.barh(
            int(core) * HEIGHT + offset + 10,
            (run[1] - run[0]).total_seconds(),
            left=(run[0] - min(start_times)).total_seconds(),
            color=run[4],
            height=HEIGHT_NO_OFFSET,
            align="edge",
        )
ax1.barh(NODE_A_START + 10, MAX_LEN, left=0, color=c_dict["memcached"], height=HEIGHT_NO_OFFSET, align="edge")


# Put a legend below current axis
# axs[0].legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
#           fancybox=True, shadow=True, ncol=5, handles=legend_elements)
# plt.legend(handles=legend_elements)
# axs[3].set_ylim([0,1000])
ax1.set_xlim(0, MAX_LEN + 5)

yticks = list(np.arange(0, 2001, 250))
ylabels = list(np.arange(0, 2.001, 0.25))
for i in range(4):
    yticks.append(NODE_A_START + (2 * i + 1) * HEIGHT / 2)
    ylabels.append(i)
ax1.set_ylabel("p95 tail latency [ms]", color="royalblue", fontdict={"fontsize": 16})
ax1.set_yticks(yticks, labels=ylabels)

ax1.set_title(f"Temporary Title", fontdict={"fontsize": 18}, pad=0)

ax1.set_ylim(0, NODE_C_END)

box = ax1.get_position()
ax1.set_position([box.x0, box.y0 + box.height * 0.1, box.width, box.height * 0.9])
ax1.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, -0.08),
    fancybox=True,
    shadow=True,
    ncol=5,
    handles=legend_elements,
    prop={"size": 16},
)

ax2.set_ylim([0, max_q * 1.25])
yticks = list(np.arange(0, max_q + 1, 25000))
ylabels = list(np.arange(0, max_q + 1, 25000))
ax2.set_yticks(yticks, ylabels)
ax2.set_ylabel("QPS", color="orange", fontdict={"fontsize": 16})
ax1.set_xlabel("Time since memcached started [s]", fontdict={"fontsize": 16})
# perf_file = open(CPU_FILE, 'r')
# perf_file = perf_file.read()
# lines = perf_file.splitlines()
# lines = [line.split() for line in lines]
# cpu_x = [(datetime.fromisoformat(line[0])-START).total_seconds() for line in lines]
# for i in range(4):
#     if i in [0,1]:
#         axs[2].plot(cpu_x, [float(line[i+1])*1000 for line in lines],alpha=0.8, label=f"CPU {i}")

#     axs[1].plot(cpu_x, [float(line[i+1]) for line in lines],alpha=0.8, label=f"CPU {i}")
# axs[1].legend()
# # plt.tight_layout()

# # plt.subplot()
# plt.xlim(0,200)

plt.savefig(fname=f"test.pdf")
