import os
import subprocess
import time
import click
import ruamel.yaml

from scripts.utils import check_output, get_jobs_info, get_node_info, get_pods_info, jobs_ready, start_cluster


@click.command()
@click.option(
    "--start", "-s", help="Flag indicating if the cluster should be started", is_flag=True, default=False, type=bool
)
def task2b(start: bool):

    DEBUG = True
    PARSEC_PATH = "./parsec-benchmarks/part2b"

    setup(start, debug=DEBUG)

    run_tests(parsec_path=PARSEC_PATH, threads=[1, 2, 4, 8], debug=DEBUG)


def setup(start: bool, debug: bool = False) -> None:
    if start:
        start_cluster("part2b.yaml", cluster_name="part2b.k8s.local", debug=debug)

        # Assign the correct label to parsec node
        for line in get_node_info(debug=debug):
            if line[0].startswith("parsec-server"):
                res = subprocess.run(
                    ["kubectl", "label", "nodes", line[0], "cca-project-nodetype=parsec"], capture_output=True
                )
                check_output(res)
    else:
        print("Skipped setting up the cluster")


def run_tests(parsec_path: str, threads: list[int], debug: bool) -> None:
    for num_threads in threads:
        for parsec_file in os.listdir(parsec_path):

            yaml = ruamel.yaml.YAML()
            yaml.preserve_quotes = True

            with open(os.path.join(parsec_path, parsec_file)) as fp:
                data = yaml.load(fp)

            # Update the number of threads in the YAML file before starting it
            data["spec"]["template"]["spec"]["containers"][0]["args"][1] = data["spec"]["template"]["spec"][
                "containers"
            ][0]["args"][1][:-1] + str(num_threads)

            with open(os.path.join(parsec_path, parsec_file), "w") as f:
                yaml.dump(data, f)

            res = subprocess.run(
                ["kubectl", "create", "-f", os.path.join(parsec_path, parsec_file)], capture_output=True
            )

            while not jobs_ready(debug=debug):
                time.sleep(5)

            jobname = ""
            for line in get_jobs_info(debug=debug):
                if line[0].startswith("parsec"):
                    jobname = line[0]
                    break

            if jobname == "":
                print("ERROR: Job name not found")
                return

            directory_path = os.path.join("./results/task2b", parsec_file.rsplit(".", 1)[0])
            os.makedirs(directory_path, exist_ok=True)

            filename = os.path.join(directory_path, f"num_threads_{num_threads}.txt")

            pod = ""
            with open(filename, "w") as f:
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
    task2b()
