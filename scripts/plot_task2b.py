import os
from itertools import cycle

import matplotlib.pyplot as plt
import seaborn as sns


MARKERS = ["o", "v", "^", "<", ">", "s", "p", "*", "h", "H", "D", "d", "P", "X"]


def parse_time(time_str) -> float:
    """Parse a time string and return the total time in seconds."""
    cleaned_time_str = time_str.rstrip("s\n").strip()
    minutes, seconds = cleaned_time_str.split("m")
    return float(minutes) * 60 + float(seconds.rstrip("s"))


def find_real_time(lines) -> str | None:
    """Extract time lines (real, user, sys) from a list of lines."""

    for line in lines:
        if line.startswith("real"):
            return line
    return None


def get_time(path: str) -> float:
    with open(path) as f:
        lines = f.readlines()
        time_lines = find_real_time(lines)

        if time_lines is None:
            raise ValueError(f"Could not find real time in {path}")

        real_time = parse_time(time_lines.split("\t")[1])
        return real_time


def plt_setup(xlim, ylim, title=None, xlabel=None, ylabel=None):
    sns.set_palette("deep")
    sns.set_style("whitegrid")
    plt.figure(figsize=(12, 8), dpi=150)
    plt.rcParams["font.size"] = 12
    plt.rcParams["font.family"] = "Arial"
    plt.grid(linestyle="--", linewidth=0.5, color="gray", which="both", alpha=0.5)
    sns.despine(left=True, bottom=True)
    plt.xlim(xlim)
    plt.ylim(ylim)
    plt.xticks([1, 2, 4, 8])
    plt.yticks([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    plt.xlabel(xlabel or "Number of Threads", labelpad=10, fontsize=12)  # Adjust labelpad and fontsize
    plt.ylabel(ylabel or "Speedup", labelpad=10, fontsize=12)
    plt.title(title or "Speedup when using multiple threads", pad=10, fontsize=12)


def plot_errorbar(x, y, xerr=None, yerr=None, label=None, color="black", marker="o"):
    plt.errorbar(x=x, y=y, xerr=xerr, yerr=yerr, fmt=marker, color=color, ecolor=color, elinewidth=2, alpha=0.7)
    plt.plot(x, y, marker, label=label, color=color, alpha=1, markersize=5, linestyle=":")


def main():
    base_folder = "results/task2b"
    thread_counts = [1, 2, 4, 8]

    plt_setup(xlim=(0.925, 8.075), ylim=(0.5, 11))
    colors = cycle(plt.rcParams["axes.prop_cycle"].by_key()["color"])

    folder_names = ["radix", "freqmine", "vips", "ferret", "blackscholes", "dedup", "canneal"]

    for i, folder in enumerate(folder_names):

        parsec_name = folder.capitalize()

        time_taken = []

        folder = os.path.join(base_folder, f"parsec-{folder}")
        base_time = get_time(os.path.join(folder, "2-num_threads_1.txt"))

        for count in thread_counts:
            file_name = f"2-num_threads_{count}.txt"
            file_path = os.path.join(folder, file_name)
            time_n = get_time(file_path)
            speedup = base_time / time_n if time_n else 0
            time_taken.append(speedup)

        plot_errorbar(
            thread_counts,
            time_taken,
            label=parsec_name,
            marker=MARKERS[i % len(MARKERS)],
            color=next(colors),
        )

    plt.legend(loc="upper left")
    plt.subplots_adjust(left=0.08, right=0.92, bottom=0.08, top=0.95)
    plt.savefig("results/task2b/plots/result.png")
    # plt.show()


if __name__ == "__main__":
    main()
