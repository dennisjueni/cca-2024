import sys
from time import sleep
import subprocess
import click
import time
import os
import yaml
import tempfile

from loguru import logger

from scripts.utils import (
    scp_command,
    ssh_command,
    start_cluster,
    run_command,
    pods_ready,
    get_node_info,
    get_pods_info,
    copy_file_to_node,
    check_output,
    env,
)

NODES = [
    "client-agent-a",
    "client-agent-b",
    "client-measure",
    "master-europe-west3-a",
    "node-a-2core",
    "node-b-4core",
    "node-c-8core",
]


@click.command()
@click.option(
    "--start", "-s", help="Flag indicating if the cluster should be started", is_flag=True, default=False, type=bool
)
def task3(start: bool):
    DEBUG = True
    NUM_ITERATIONS = 1

    if start:
        # setup cluster using kops and part3.yaml
        env = start_cluster("part3.yaml")
        start_memcached(env)
        start_mcperf(env)
        schedule_batch_jobs(env)

    #   - After previous are running: Start pods with batch jobs (`kubectl create -f batch-job{j}.yaml` jor j in {blackscholes, ...})


def start_memcached(env: dict) -> None:
    # Start memcached pod using `kubectl create -f memcached.yaml`
    path = os.path.join(".", "memcache-t1-cpuset-part3.yaml")
    run_command(f"kubectl create -f {path}".split())


def schedule_batch_jobs(env: dict) -> None:
    # blackscholes,canneal,dedup,ferret,freqmine,radix,vips
    # TODO
    schedule_single_job("blackscholes", "blackscholes", "node-b-4core", "4,5,6,7", 3)
    schedule_single_job("canneal", "canneal", "node-b-4core", "4,5,6,7", 3)
    schedule_single_job("dedup", "dedup", "node-b-4core", "4,5,6,7", 3)
    schedule_single_job("ferret", "ferret", "node-b-4core", "4,5,6,7", 3)
    schedule_single_job("freqmine", "freqmine", "node-b-4core", "4,5,6,7", 3)
    schedule_single_job("radix", "radix", "node-b-4core", "4,5,6,7", 3)
    schedule_single_job("vips", "vips", "node-b-4core", "4,5,6,7", 3)


def schedule_single_job(job_name: str, benchmark: str, node_selector: str, cores: str, nr_threads: int) -> None:
    # Start a single job using `kubectl create -f batch-job.yaml`
    file = modified_yaml_file(
        os.path.join(PARSEC_PATH, f"parsec-{job_name}.yaml"),
        selector=__node_selector(node_selector),
        container_args=__container_args(cores, benchmark, nr_threads),
    )
    run_command(f"kubectl create -f {file.name}".split())
    file.close()


def memcached_ip(env: dict) -> str:
    info = get_pods_info()
    for line in info:
        if line[0].startswith("memcached"):
            return line[5]


def is_memcached_ready(env: dict) -> bool:
    info = get_pods_info()
    for line in info:
        if line[0].startswith("memcached"):
            if line[1] == "1/1" and line[2] == "Running":
                return True
    return False


def modified_yaml_file(file_path, **kwargs):
    """
    Usage example:
        modify_yaml_file("file.yaml", lambda file: run_command(f"cat {file.name}"), value1=([key1, subkey2], "modified_value"))
    """
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

    # Traverse the attribute path and update the value
    for attribute_path, new_value in kwargs.values():
        current_node = data
        for key in attribute_path[:-1]:
            current_node = current_node[key]  # can be a list or a dict
        if current_node:
            current_node[attribute_path[-1]] = new_value
        else:
            raise ValueError(f"Attribute path '{attribute_path}' not found in YAML")

    # Write modified data to a temporary file
    temp_file = tempfile.NamedTemporaryFile(mode="w")
    yaml.dump(data, temp_file, default_flow_style=False)
    return temp_file


def start_mcperf(env: dict) -> None:
    # Start mcperf pod(s) using `kubectl create -f mcperf.yaml`
    # use make_mcperf.sh script to build mcperf on client-agent and client-measure
    assert is_memcached_ready(), "Memcached pod not ready"
    d = {}
    for line in get_node_info(d):
        if line[0].startswith("client-agent-") or line[0].startswith("client-measure-"):
            # copy make_mcperf.sh to the node
            node = line[0]
            logger.info(f"Copying mcperf files to {line[0]}")
            res = scp_command(
                "./install_mcperf.sh",  # local file
                "~/install_mcperf.sh",  # remote file
                node,
            )
            # run make_mcperf.sh on the node
            res = ssh_command(node, "chmod +x ~/install_mcperf.sh && ~/install_mcperf.sh")
            #
            if node.startswith("client-agent-a"):
                res = ssh_command(node, "./mcperf -T 2 -A")
            elif node.startswith("client-agent-b"):
                res = ssh_command(node, "./mcperf -T 4 -A")
            elif node.startswith("client-measure"):
                MEMCACHED_IP = memcached_ip()
                res = ssh_command(node, f"./mcperf -s {MEMCACHED_IP} --loadonly")
                res = ssh_command(
                    node,
                    f"./mcperf -s {MEMCACHED_IP} -a INTERNAL_AGENT_A_IP -a INTERNAL_AGENT_B_IP \
                    --noload -T 6 -C 4 -D 4 -Q 1000 -c 4 -t 10 --scan 30000:30500:5",
                )


def __taskset_command(cores: str, benchmark: str, nr_threads: int) -> list:
    # args: ["-c", "taskset -c 4,5,6 ./run -a run -S parsec -p canneal -i native -n 3"]
    return ["-c", f"taskset -c {cores} ./run -a run -S parsec -p {benchmark} -i native -n {nr_threads}"]


def __container_args(cores: str, benchmark: str, nr_threads: int) -> tuple:
    return ["spec", "template", "spec", "containers", 0, "args"], __taskset_command(cores, benchmark, nr_threads)


def __node_selector(selector_value: str) -> list:
    return ["spec", "template", "spec", "nodeSelector", "cca-project-nodetype"], selector_value


####### TESTS #######

PARSEC_PATH = os.path.join(".", "parsec-benchmarks", "part3")

if __name__ == "__main__":
    file = modified_yaml_file(
        os.path.join(PARSEC_PATH, "parsec-blackscholes.yaml"),
        selector=__node_selector("node-b-4core"),
        container_args=__container_args("4,5,6,7", "blackscholes", 3),
    )
    subprocess.run(["cat", file.name])
    file.close()
