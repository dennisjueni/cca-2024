import os


def parse_time(time_str):
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


def read_times(folder):
    """Read execution times from text files in a given folder."""
    times = {}
    for filename in os.listdir(folder):
        with open(os.path.join(folder, filename)) as f:
            lines = f.readlines()
            time_lines = find_real_time(lines)

            if time_lines is None:
                raise ValueError(f"Could not find real time in {filename}")

            real_time = parse_time(time_lines.split("\t")[1])
            times[filename] = real_time
    return times


def print_latex_table(data, order, jobs_order):
    """Prints the data in LaTeX table format with specified headers and order."""
    print("\\begin{center}")
    print("\\begin{tabular}{ |c|c|c|c|c|c|c|c| }")
    print("\\hline")

    # Header
    print(
        "\\textbf{Workload} & \\texttt{\\textbf{none}} & \\texttt{\\textbf{cpu}} & \\texttt{\\textbf{l1d}} & \\texttt{\\textbf{l1i}} & \\texttt{\\textbf{l2}} & \\texttt{\\textbf{llc}} & \\texttt{\\textbf{memBW}}  \\\\"
    )
    print("\\hline\\hline")

    # Data rows
    for job in jobs_order:
        print(job + " &", end=" ")
        row_data = [data[job][h] for h in order]

        # Print the first column without color
        print(f"{row_data[0]:.2f}", end=" ")

        for d in row_data[1:]:
            print("&", end=" ")
            if d <= 1.3:
                print("\\cellcolor{Green}", end=" ")
            elif d <= 2:
                print("\\cellcolor{YellowOrange}", end=" ")
            else:
                print("\\cellcolor{Red}", end=" ")
            print(f"{d:.2f}", end=" ")

        print("\\\\ \\hline")

    print("\\end{tabular}")
    print("\\end{center}")


def main():
    base_folder = "results/task2a"
    no_interference_folder = os.path.join(base_folder, "no_interference")

    # Read baseline execution times
    baseline_times = read_times(no_interference_folder)

    columns_order = ["none", "cpu", "l1d", "l1i", "l2", "llc", "memBW"]
    jobs_order = ["blackscholes", "canneal", "dedup", "ferret", "freqmine", "radix", "vips"]

    data = {job: {"none": 1.00} for job in jobs_order}

    interference_to_column = {
        "ibench-cpu": "cpu",
        "ibench-l1d": "l1d",
        "ibench-l1i": "l1i",
        "ibench-l2": "l2",
        "ibench-llc": "llc",
        "ibench-membw": "memBW",
    }

    for interference in os.listdir(base_folder):
        if interference == "no_interference":
            continue
        column_name = interference_to_column.get(interference)

        if not column_name:
            raise ValueError(f"Unknown interference type: {interference}")

        interference_folder = os.path.join(base_folder, interference)
        interference_times = read_times(interference_folder)

        for job_filename, time in interference_times.items():
            # Normalize job name
            job_name = job_filename.replace("parsec-", "").replace(".txt", "")
            if job_name not in data:
                raise ValueError(f"Unknown job name: {job_name}")

            # Calculate normalized time and update the data structure
            normalized_time = round(time / baseline_times[job_filename], 2)
            data[job_name][column_name] = normalized_time

    print_latex_table(data, columns_order, jobs_order)


if __name__ == "__main__":
    main()
