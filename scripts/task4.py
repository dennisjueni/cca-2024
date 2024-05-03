import time
import click
import sys


# add scripts to sys path
try:
    sys.path.append("scripts")
except Exception as e:
    print(e)


from scripts.task3 import install_mcperf
from utils import *
import os
from loguru import logger
from task4_config import *
import tempfile

LOG_RESULTS = os.path.join(".", "results-part4", time.strftime("%Y-%m-%d-%H-%M"))
os.makedirs(LOG_RESULTS, exist_ok=True)


@click.command()
@click.option(
    "--start", "-s", help="Flag indicating if the cluster should be started", is_flag=True, default=False, type=bool
)
def task4(start: bool):
    if start:
        start_cluster(part=Part.PART4)
        logger.info("Started cluster for task 4")

    copy_task4()
    install_memcached()
    # TODO: start memcached server
    install_mcperf(False)  # install dynamic mcperf on agent and measure
    start_mcperf()


def copy_task4():
    requirements = "requirements_part4.txt"
    source_folder = os.path.join(".", "scripts")
    destination = os.path.join("~")
    node_info = get_node_info()
    for line in node_info:
        if line[0].startswith(MEMCACHED):
            for file_name in os.listdir(source_folder):
                if (
                    (file_name.startswith("task4_") and file_name.endswith(".py"))
                    or (file_name == "utils.py")
                    or (file_name == requirements)
                ):
                    source_file = os.path.join(source_folder, file_name)
                    copy_file_to_node(line[0], source_file, destination)

            logger.info(f"Copied python scripts to {line[0]}")

            ssh_command(line[0], f"sudo apt install python3-pip -y")
            ssh_command(line[0], f"pip install -r {requirements}")

            logger.info(f"Installed requirements to {line[0]}")


def install_memcached():
    node_info = get_node_info()
    for line in node_info:
        if line[0].startswith(MEMCACHED):
            ssh_command(line[0], "sudo apt update")
            ssh_command(line[0], "sudo apt install -y memcached libmemcached-tools")
            # copy only once, to use as a starting point
            # copy_file_from_node(line[0], "/etc/memcached.conf", os.path.join(".", "scripts"))
            with open("scripts/memcached.conf", "r") as f:
                content = (
                    f.read()
                    .replace("MEMCACHED_INTERNAL_IP", get_node_ip("memcache-server"))
                    .replace("MEMORY_LIMIT", "1024")
                    .replace("NUM_THREADS", f"{NUM_THREADS_MEMCACHED}"))
            with tempfile.NamedTemporaryFile(mode="w") as temp_file:
                temp_file.write(content)
                copy_file_to_node(line[0], temp_file.name, "~/memcached.conf")
            ssh_command(line[0], "sudo mv ~/memcached.conf /etc/memcached.conf")
            ssh_command(line[0], "sudo systemctl restart memcached")
            logger.info(f"Installed memcached to {line[0]}")


def start_mcperf():
    logger.info("########### Starting Memcached on all 2 machines ###########")
    node_info = get_node_info()
    client_agent_name = None
    client_measure_name = None

    for line in node_info:
        if line[0].startswith("client-agent"):
            client_agent_name = line[0]
        elif line[0].startswith("client-measure"):
            client_measure_name = line[0]

    client_agent_ip = get_node_ip("client-agent")
    memcached_ip = get_node_ip("memcache-server")

    mcperf_agent_command = "./memcache-perf-dynamic/mcperf -T 16 -A"
    log_agent_file = open(os.path.join(LOG_RESULTS, "mcperf_agent.txt"), "w")
    res = ssh_command(client_agent_name, mcperf_agent_command, is_async=True, file=log_agent_file)

    mc_perf_measure_command = f"./memcache-perf-dynamic/mcperf -s {memcached_ip} --loadonly && ./memcache-perf-dynamic/mcperf -s {memcached_ip} -a {client_agent_ip} --noload -T 16 -C 4 -D 4 -Q 1000 -c 4 -t 10 --qps_interval 2 --qps_min 5000 --qps_max 100000"
    log_file = open(os.path.join(LOG_RESULTS, "mcperf.txt"), "w")
    res = ssh_command(client_measure_name, mc_perf_measure_command, is_async=True, file=log_file)


if __name__ == "__main__":
    task4()
