import sys
from time import sleep
import subprocess
import click
import time
import os

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

    # TODO : `memcached` and workload creation with pods (`kubectl`) instead of setting up cluster (`kops`) - modify yaml files
    #   - Start `memcached` pod (`kubectl create -f memcached.yaml`)
    #   - Start `mcperf` pod(s) (`kubectl create -f mcperf.yaml`)
    #      - sprecial `mcperf` version on `client-agent-` & `client-measure` machines (https://github.com/eth-easl/memcache-perf-dynamic)
    #      - `make` on `client-agent-` & `client-measure` machines
    #      - ? something like : `gcloud compute ssh ... ubuntu@$(kubectl get nodes -o wide | grep client-agent | awk '{print $1}')`
    #   - After previous are running: Start pods with batch jobs (`kubectl create -f batch-job{j}.yaml` jor j in {blackscholes, ...})


def start_memcached(env: dict) -> None:
    # Start memcached pod using `kubectl create -f memcached.yaml`
    # TODO : Set up 'part3/memcache-t1-cpuset.yaml'
    pass


def start_mcperf(env: dict) -> None:
    # Start mcperf pod(s) using `kubectl create -f mcperf.yaml`
    # use make_mcperf.sh script to build mcperf on client-agent and client-measure
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
                # TODO : select pod with memcached to get IP for pod "some-memcached"
                MEMCACHED_IP = None  # TODO
                res = ssh_command(node, f"./mcperf -s {MEMCACHED_IP} --loadonly")
                res = ssh_command(node, f"./mcperf -s {MEMCACHED_IP} -a INTERNAL_AGENT_A_IP -a INTERNAL_AGENT_B_IP \
                    --noload -T 6 -C 4 -D 4 -Q 1000 -c 4 -t 10 \
                    --scan 30000:30500:5
                    ")
