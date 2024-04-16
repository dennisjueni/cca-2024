import sys
from time import sleep
import subprocess
import click
import time
import os

from scripts.utils import (
    start_cluster,
    run_command,
    pods_ready,
    get_node_info,
    get_pods_info,
    copy_file_to_node,
    check_output,
)


@click.command()
@click.option(
    "--start", "-s", help="Flag indicating if the cluster should be started", is_flag=True, default=False, type=bool
)
def task3(start: bool):
    DEBUG = True
    NUM_ITERATIONS = 1

    if start:
        start_cluster("part3.yaml", debug=DEBUG)  # TODO : Waits for cluster to be ready?

    # TODO : `memcached` and workload creation with pods (`kubectl`) instead of setting up cluster (`kops`) - modify yaml files
    #   - Start `memcached` pod (`kubectl create -f memcached.yaml`)
    #   - Start `mcperf` pod(s) (`kubectl create -f mcperf.yaml`)
    #      - sprecial `mcperf` version on `client-agent-` & `client-measure` machines (https://github.com/eth-easl/memcache-perf-dynamic)
    #      - `make` on `client-agent-` & `client-measure` machines
    #      - ? something like : `gcloud compute ssh ... ubuntu@$(kubectl get nodes -o wide | grep client-agent | awk '{print $1}')`
    #   - After previous are running: Start pods with batch jobs (`kubectl create -f batch-job{j}.yaml` jor j in {blackscholes, ...})
