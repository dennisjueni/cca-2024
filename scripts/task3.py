from io import TextIOWrapper
import sys
import click
import time
import os

from time import sleep
from typing import Tuple
from loguru import logger

from scripts.job import Job
from scripts.delete import delete_pods
from scripts.utils import (
    Part,
    copy_file_to_node,
    pods_completed,
    ssh_command,
    start_cluster,
    run_command,
    pods_ready,
    get_node_info,
    get_pods_info,
    get_node_ip,
    get_pod_ip,
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
PROCESSES = []
LOG_RESULTS = os.path.join(".", "results-part3", time.strftime("%Y-%m-%d-%H-%M"))
os.makedirs(LOG_RESULTS, exist_ok=True)


@click.command()
@click.option(
    "--start", "-s", help="Flag indicating if the cluster should be started", is_flag=True, default=False, type=bool
)
def task3(start: bool):
    try:
        if start:
            # setup cluster using kops and part3.yaml
            start_cluster(part=Part.PART3)

        start_memcached()

        install_mcperf()

        log_file, error_file = start_mcperf()

        schedule_batch_jobs()

        # wait for jobs to finish
        while not pods_completed():
            sleep(5)
            log_file.flush()
            error_file.flush()

        log_time()

    except Exception as e:
        logger.error(e)
    finally:
        # cleanup
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

    logger.success("########### Memcached started ###########")


def install_mcperf() -> None:
    # memcached should already be ready since we wait for it in install_memcached
    assert is_memcached_ready(), "Memcached pod not ready"

    source_path = "./scripts/install_mcperf_dynamic.sh"
    destination_path = "~/install_mcperf_dynamic.sh"

    for line in get_node_info():
        if line[0].startswith("client-agent-") or line[0].startswith("client-measure-"):

            # First we check if we have already copied the file to the node, if so, we do not do it again
            check_command = f"test -f {destination_path} && echo 'already installed' || echo '-'"
            res = ssh_command(
                line[0],
                check_command,
                is_async=False,
            )

            if "already installed" in res.stdout.decode("utf-8"):  # type: ignore
                logger.info(f"Memcached already installed on {line[0]}")
                continue

            copy_file_to_node(line[0], source_path=source_path, destination_path=destination_path)
            logger.info(f"Copied the mcperf install script to {line[0]}")

            install_command = f"chmod +x {destination_path} && {destination_path}"
            ssh_command(
                line[0],
                install_command,
                is_async=False,
            )

    logger.success("########### Finished Installing mcperf on all 3 machines ###########")


def start_mcperf() -> Tuple[TextIOWrapper, TextIOWrapper]:
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

    mcperf_agent_a_command = "./memcache-perf-dynamic/mcperf -T 2 -A"
    res = ssh_command(
        client_agent_a_name,
        mcperf_agent_a_command,
        is_async=True,
    )
    PROCESSES.append(res)

    mcperf_agent_b_command = "./memcache-perf-dynamic/mcperf -T 4 -A"
    res = ssh_command(
        client_agent_b_name,
        mcperf_agent_b_command,
        is_async=True,
    )
    PROCESSES.append(res)

    time.sleep(5)

    mc_perf_measure_load_command = f"~/memcache-perf-dynamic/mcperf -s {memcached_ip} --loadonly"
    res = ssh_command(client_measure_name, mc_perf_measure_load_command, is_async=True)
    PROCESSES.append(res)

    log_file = open(os.path.join(LOG_RESULTS, "mcperf.txt"), "w")
    error_file = open(os.path.join(LOG_RESULTS, "mcperf.error"), "w")
    mc_perf_measure_start_command = f"./memcache-perf-dynamic/mcperf -s {memcached_ip} -a {client_agent_a_ip} -a {client_agent_b_ip} --noload -T 6 -C 4 -D 4 -Q 1000 -c 4 -t 10 --scan 30000:30500:5"
    logger.info(f"Executing mcperf on {client_measure_name} - command: `{mc_perf_measure_start_command}`")
    res = ssh_command(
        client_measure_name,
        mc_perf_measure_start_command,
        is_async=True,
        stdout=log_file.fileno(),
        stderr=error_file.fileno(),
    )
    PROCESSES.append(res)

    return log_file, error_file


def schedule_batch_jobs() -> None:
    """blackscholes,canneal,dedup,ferret,freqmine,radix,vips

    node a has 2 high performance cores with 2GB of memroy,
    node b has 4 high performance cores with 32GB of memory,
    node c has 8 low performance cores with 32GB of memory

    learnings:
        scheduling memcached on one core of node a fulfills the SLO
        radix runs out of memory on the small memory node, so schedule it on node b or c
        schedule canneal on a high performance node, as it has bad parallelism and needs a lot of CPU time
        schedule dedup on the second core with memcached, as it also has bad parallelism and does not run out of memory on the small node
    """

    # run 14-34
    # schedule_single_job("blackscholes", "blackscholes", "node-c-8core", "4,5", 2)  # fourth
    # schedule_single_job("canneal", "canneal", "node-b-4core", "2,3", 2)  # fifth
    # schedule_single_job("radix", "radix", "node-c-8core", "6,7", 2, benchmark_suite="splash2x")  # first
    # schedule_single_job("ferret", "ferret", "node-b-4core", "0,1,2", 3)  # seventh (almost 6th)
    # schedule_single_job("freqmine", "freqmine", "node-c-8core", "0,1,2,3,4,6,7", 6)  # sixth
    # schedule_single_job("dedup", "dedup", "node-a-2core", "1", 1)  # second
    # schedule_single_job("vips", "vips", "node-c-8core", "0,1", 2)  # third

    # TODO : Please Check if depends_on makes sense and works :-)
    # run 17-55
    # ferret_job = Job("ferret", "ferret", "node-b-4core", "0,1,2,3", 4)
    # radix_job = Job("radix", "radix", "node-b-4core", "2,3", 2, benchmark_suite="splash2x")
    # vips_job = Job("vips", "vips", "node-b-4core", "2,3", 2, depends_on=[radix_job])
    # freqmine_job = Job("freqmine", "freqmine", "node-c-8core", "0,1,2,3,4,5", 8)
    # blackscholes_job = Job("blackscholes", "blackscholes", "node-c-8core", "4,5", 2)
    # canneal_job = Job("canneal", "canneal", "node-c-8core", "6,7", 2)
    # dedup_job = Job("dedup", "dedup", "node-a-2core", "1", 1)
    # jobs = [blackscholes_job, canneal_job, dedup_job, ferret_job, freqmine_job, radix_job, vips_job]

    # run 18-17
    # ferret_job = Job("ferret", "ferret", "node-b-4core", "0,1,2", 3)
    # canneal_job = Job("canneal", "canneal", "node-b-4core", "2,3", 2)

    # radix_job = Job("radix", "radix", "node-c-8core", "6,7", 2, benchmark_suite="splash2x")
    # vips_job = Job("vips", "vips", "node-c-8core", "6,7", 2, depends_on=[radix_job])
    # freqmine_job = Job("freqmine", "freqmine", "node-c-8core", "0,1,2,3,4,5,6,7", 8)
    # blackscholes_job = Job("blackscholes", "blackscholes", "node-c-8core", "4,5", 2)

    # dedup_job = Job("dedup", "dedup", "node-a-2core", "1", 1)
    # jobs = [blackscholes_job, canneal_job, dedup_job, ferret_job, freqmine_job, radix_job, vips_job]

    ferret_job = Job("ferret", "ferret", "node-b-4core", "0,1,2", 3)
    canneal_job = Job("canneal", "canneal", "node-b-4core", "2,3", 2)

    freqmine_job = Job("freqmine", "freqmine", "node-c-8core", "0,1,2,3,4,5,6,7", 8)
    blackscholes_job = Job("blackscholes", "blackscholes", "node-c-8core", "4,5", 2)
    radix_job = Job("radix", "radix", "node-c-8core", "6,7", 2, benchmark_suite="splash2x")
    vips_job = Job("vips", "vips", "node-c-8core", "6,7", 2, depends_on=[radix_job])

    dedup_job = Job("dedup", "dedup", "node-a-2core", "1", 1)

    # start in this order, the longer jobs starting first
    jobs = [ferret_job, freqmine_job, canneal_job, blackscholes_job, dedup_job, radix_job, vips_job]

    # maybe use apply in the future
    # for job in jobs:
    #     job.apply()
    # sleep(5)

    while True:
        unstarted_jobs = [job for job in jobs if not job.started]
        if len(unstarted_jobs) == 0:
            break
        for job in unstarted_jobs:
            job.start()
        sleep(2)


def is_memcached_ready() -> bool:
    return pods_ready()


def log_time():
    get_command = "kubectl get pods -o json > results.json"
    os.system(get_command)
    get_command = f"python3 get_time.py results.json > {os.path.join(LOG_RESULTS, 'execution_time.txt')}"
    os.system(get_command)


if __name__ == "__main__":
    task3()
