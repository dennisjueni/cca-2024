import sys
import click
import time
import os
import subprocess

from time import sleep
from loguru import logger

from scripts.job import Job
from scripts.delete import delete_pods
from scripts.utils import (
    Part,
    install_mcperf,
    is_memcached_ready,
    pods_completed,
    services_ready,
    ssh_command,
    start_cluster,
    run_command,
    pods_ready,
    get_node_info,
    get_pods_info,
    get_node_ip,
    get_pod_ip,
)


PROCESSES = []
LOG_RESULTS = os.path.join(".", "results-part3", "final_runs", time.strftime("%Y-%m-%d-%H-%M"))
os.makedirs(LOG_RESULTS, exist_ok=True)


@click.command()
@click.option(
    "--start", "-s", help="Flag indicating if the cluster should be started", is_flag=True, default=False, type=bool
)
def task3(start: bool):
    try:
        if start:
            start_cluster(part=Part.PART3)

        start_memcached()

        install_mcperf()

        start_mcperf()

        # We need this so that we get mcperf logs before we start all the benchmarks
        sleep(60)

        schedule_batch_jobs()

        # wait for all PARSEC benchmarks to finish
        while not pods_completed():
            sleep(5)

        # We need this so that we get mcperf logs until all benchmarks have finished
        sleep(60)

        log_time()

    except Exception as e:
        logger.error(e)
    finally:
        for process in PROCESSES:
            process.kill()

        delete_pods()


def start_memcached() -> None:
    logger.info("########### Starting Memcached ###########")

    # If Memcached is already running, we don't need to do anything
    if is_memcached_ready():
        logger.info("########### Memcached already running ###########")
        return

    create_memcached_command = ["kubectl", "create", "-f", "memcache-t1-cpuset-part3.yaml"]
    run_command(create_memcached_command)

    expose_memcached_command = [
        "kubectl",
        "expose",
        "pod",
        "some-memcached",
        "--name",
        "some-memcached-11211",
        "--type",
        "LoadBalancer",
        "--port",
        "11211",
        "--protocol",
        "TCP",
    ]
    run_command(expose_memcached_command)

    while not pods_ready():
        time.sleep(5)

    # Wait for the memcached service to be exposed!!
    while not services_ready():
        time.sleep(5)

    logger.success("########### Memcached started ###########")


def start_mcperf() -> None:
    logger.info("########### Starting Memcached on all 3 machines ###########")
    global PROCESSES

    node_info = get_node_info()
    pod_info = get_pods_info()

    client_agent_a_name = None
    client_agent_b_name = None
    client_measure_name = None
    memcached_ip = get_pod_ip("some-memcached")
    client_agent_a_ip = get_node_ip("client-agent-a")
    client_agent_b_ip = get_node_ip("client-agent-b")

    for line in node_info:
        if line[0].startswith("client-agent-a"):
            client_agent_a_name = line[0]
        elif line[0].startswith("client-agent-b"):
            client_agent_b_name = line[0]
        elif line[0].startswith("client-measure"):
            client_measure_name = line[0]

    for line in pod_info:
        if line[0].startswith("some-memcached"):
            memcached_ip = line[5]

    if (
        client_agent_a_name is None
        or client_agent_b_name is None
        or client_measure_name is None
        or memcached_ip is None
    ):
        print("Could not find client-agent-a, client-agent-b, client-measure, or memcached node")
        sys.exit(1)

    f_a = open(os.path.join(LOG_RESULTS, "mcperf_a.txt"), "w")
    f_b = open(os.path.join(LOG_RESULTS, "mcperf_b.txt"), "w")

    mcperf_agent_a_command = "./memcache-perf-dynamic/mcperf -T 2 -A"
    res = ssh_command(client_agent_a_name, mcperf_agent_a_command, is_async=True, file=f_a)
    PROCESSES.append(res)

    time.sleep(5)

    mcperf_agent_b_command = "./memcache-perf-dynamic/mcperf -T 4 -A"
    res = ssh_command(client_agent_b_name, mcperf_agent_b_command, is_async=True, file=f_b)
    PROCESSES.append(res)

    time.sleep(5)

    log_file = open(os.path.join(LOG_RESULTS, "mcperf.txt"), "w")

    mc_perf_measure_command = f"./memcache-perf-dynamic/mcperf -s {memcached_ip} --loadonly && ./memcache-perf-dynamic/mcperf -s {memcached_ip} -a {client_agent_a_ip} -a {client_agent_b_ip} --noload -T 6 -C 4 -D 4 -Q 1000 -c 4 -t 10 --scan 30000:30500:5"

    res = ssh_command(client_measure_name, mc_perf_measure_command, is_async=True, file=log_file)
    PROCESSES.append(res)


def schedule_batch_jobs() -> None:
    """blackscholes,canneal,dedup,ferret,freqmine,radix,vips

    node a has 2 high performance cores with 2GB of memroy,
    node b has 4 high performance cores with 32GB of memory,
    node c has 8 low performance cores with 32GB of memory
    """

    # Node A
    blackscholes_job = Job("blackscholes", "blackscholes", "node-a-2core", "1", 1)

    # Node B
    canneal_job = Job("canneal", "canneal", "node-b-4core", "0,1", 2)
    ferret_job = Job("ferret", "ferret", "node-b-4core", "2,3", 2)

    # Node C
    freqmine_job = Job("freqmine", "freqmine", "node-c-8core", "0,1,2,3,4", 5)
    vips_job = Job("vips", "vips", "node-c-8core", "5,6", 2)
    radix_job = Job("radix", "radix", "node-c-8core", "7", 1, benchmark_suite="splash2x")
    dedup_job = Job("dedup", "dedup", "node-c-8core", "7", 1, depends_on=[radix_job])

    jobs = [radix_job, freqmine_job, vips_job, canneal_job, ferret_job, blackscholes_job, dedup_job]

    while True:
        unstarted_jobs = [job for job in jobs if not job.started]
        if len(unstarted_jobs) == 0:
            break
        for job in unstarted_jobs:
            job.start()
        sleep(1)


def log_time():
    get_command = f"kubectl get pods -o json > {os.path.join(LOG_RESULTS, 'results.json')}"
    os.system(get_command)
    get_command = f"python3 get_time.py {os.path.join(LOG_RESULTS, 'results.json')} > {os.path.join(LOG_RESULTS, 'execution_time.txt')}"
    os.system(get_command)


if __name__ == "__main__":
    task3()
