import time
import click
from scripts.task3 import install_mcperf
from utils import *
import os
from loguru import logger
from task4_config import *

LOG_RESULTS = os.path.join(".", "results-part4" , time.strftime("%Y-%m-%d-%H-%M"))
os.makedirs(LOG_RESULTS, exist_ok=True)

@click.command()
@click.option(
    "--start", "-s", help="Flag indicating if the cluster should be started", is_flag=True, default=False, type=bool
)
def task4(start: bool):
    start_cluster_4()
    copy_task4()

    # TODO start memcached server

    # TODO start mcperf


def copy_task4():
    requirements = "requirements_part4.txt"
    source_folder = os.join(".", "scripts")
    destination = os.join("~")
    node_info = get_node_info()
    for line in node_info:
        if line[0].startswith(MEMCACHED):
            for file_name in os.listdir(source_folder):
                if (
                    (file_name.startswith("task4_") and file_name.endswith(".py"))
                    or (file_name == "utils.py")
                    or (file_name == requirements)
                ):
                    source_file = os.join(source_folder, file_name)
                    copy_file_to_node(line[0], source_file, destination)

            logger.info(f"Copied python scripts to {line[0]}")

            ssh_command(line[0], f"pip install -r {requirements}")

            logger.info(f"Installed requirements to {line[0]}")


def install_memcached():
    node_info = get_node_info()
    for line in node_info:
        if line[0].startswith(MEMCACHED):
            ssh_command(line[0], f"sudo apt update")
            ssh_command(line[0], f"sudo apt install -y memcached libmemcached-tools")
            copy_file_from_node(line[0], "/etc/memcached.conf", os.join(".", "scripts"))


def start_cluster_4():
    start_cluster(part=Part.PART4)
    logger.info("Started cluster for task 4")

    start_memcached()
    install_mcperf()  # install dynamic mcperf on agent and measure
    start_mcperf()


def start_mcperf():
    logger.info("########### Starting Memcached on all 3 machines ###########")
    node_info = get_node_info()
    pod_info = get_pods_info()
    client_agent_ip = get_node_ip("client-agent")
    # TODO !!!
    res = ssh_command(client_agent_b_name, mcperf_agent_b_command, is_async=True, file=f_b)
    client_measure_ip = get_node_ip("client-measure")
    memcached_ip = get_node_ip("memcache-server")
    mcperf_agent_command = "./memcache-perf-dynamic/mcperf -T 16 -A"
    mc_perf_measure_command = f"./memcache-perf-dynamic/mcperf -s {memcached_ip} --loadonly && ./memcache-perf-dynamic/mcperf -s {memcached_ip} -a {client_agent_ip} --noload -T 6 -C 4 -D 4 -Q 1000 -c 4 -t 10 --scan 30000:30500:5"
    
    log_file = open(os.path.join(LOG_RESULTS, "mcperf.txt"), "w")
    res = ssh_command(client_measure_ip, mc_perf_measure_command, is_async=True, file=log_file)
 
    for line in node_info:
        if line[0].startswith("client-agent"):
            

if __name__ == "__main__":
    copy_task4()
