import time
import click
import os
import subprocess

from scripts.utils import (
    check_output,
    get_jobs_info,
    get_node_info,
    get_pods_info,
    jobs_ready,
    pods_ready,
    start_cluster,
)


@click.command()
@click.option(
    "--start", "-s", help="Flag indicating if the cluster should be started", is_flag=True, default=False, type=bool
)
def task2a(start: bool):

    DEBUG = True
    INTERFERENCE_PATH = "./interference-2a"
    PARSEC_PATH = "./parsec-benchmarks/part2a"

    setup(start, debug=DEBUG)

    run_tests(INTERFERENCE_PATH, PARSEC_PATH, debug=DEBUG)


def setup(start: bool, debug: bool = False) -> None:
    if start:
        start_cluster("part2a.yaml", cluster_name="part2a.k8s.local", debug=debug)

        # Assign the correct label to parsec node
        for line in get_node_info(debug=debug):
            if line[0].startswith("parsec-server"):
                res = subprocess.run(
                    ["kubectl", "label", "nodes", line[0], "cca-project-nodetype=parsec"], capture_output=True
                )
                check_output(res)
    else:
        print("Skipped setting up the cluster")


def run_tests(interference_path: str, parsec_path: str, debug: bool) -> None:
    # First run a loop to start the interference pods one after another, then run the parsec pods

    for interference_file in os.listdir(interference_path):
        res = subprocess.run(
            ["kubectl", "create", "-f", os.path.join(interference_path, interference_file)], capture_output=True
        )

        # Wait until the interference pod is started
        while not pods_ready(debug=debug):
            time.sleep(10)

        for parsec_file in os.listdir(parsec_path):
            res = subprocess.run(
                ["kubectl", "create", "-f", os.path.join(parsec_path, parsec_file)], capture_output=True
            )

            while not jobs_ready(debug=debug):
                time.sleep(10)

            # We need to get the name of the job to get the logs of it

            jobname = ""
            for line in get_jobs_info(debug=debug):
                if line[0].startswith("parsec"):
                    jobname = line[0]
                    break

            if jobname == "":
                print("ERROR: Job name not found")
                return

            filename = (
                f"results/task2a/interference_{interference_file.rsplit('.', 1)[0]}_{parsec_file.rsplit('.', 1)[0]}"
            )

            pod = ""
            with open(filename + ".txt", "w") as f:
                for line in get_pods_info(debug=debug):
                    if line[0].startswith(jobname):
                        pod = line[0]
                        break

                if pod == "":
                    print("ERROR: Pod name not found")
                    return

                res = subprocess.run(["kubectl", "logs", pod], stdout=f)

            res = subprocess.run(["kubectl", "delete", "jobs", "--all"])

        res = subprocess.run(["kubectl", "delete", "pods", "--all"])


if __name__ == "__main__":
    task2a()
