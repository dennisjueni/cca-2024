import time
import click
import sys


# add scripts to sys path
try:
    sys.path.append("scripts")
except Exception as e:
    print(e)


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
    try:
        if start:
            start_cluster(part=Part.PART4)

        copy_task4()
        install_memcached_and_docker()

        install_mcperf(False)  # install dynamic mcperf on agent and measure
        start_mcperf()

        # time.sleep(20)

        start_memcached_controller()
    finally:
        stop_comand = "sudo docker stop $(docker ps -a -q)"
        remove_command = "sudo docker rm $(docker ps -a -q)"
        for line in get_node_info():
            if line[0].startswith(MEMCACHED):
                ssh_command(line[0], stop_comand)
                ssh_command(line[0], remove_command)


def start_memcached_controller():
    logger.info("########### Starting Memcached Controller ###########")
    node_info = get_node_info()
    memcached_name = None

    for line in node_info:
        if line[0].startswith(MEMCACHED):
            memcached_name = line[0]

    if memcached_name is None:
        logger.error("Could not find the controller node")
        sys.exit(1)

    ssh_command(memcached_name, "python3 ~/task4_controller.py")

    logger.success(f"Started memcached controller on {memcached_name}")


def copy_task4():
    requirements_path = "requirements_part4.txt"
    utils_path = "utils.py"

    source_folder = os.path.join(".", "scripts")
    destination = os.path.join("~")

    for line in get_node_info():
        if line[0].startswith(MEMCACHED):
            for file_name in os.listdir(source_folder):
                if (
                    (file_name.startswith("task4_") and file_name.endswith(".py"))
                    or (file_name == utils_path)
                    or (file_name == requirements_path)
                ):
                    source_file = os.path.join(source_folder, file_name)
                    copy_file_to_node(line[0], source_file, destination)

            logger.info(f"Copied python scripts to {line[0]}")

            ssh_command(line[0], f"sudo apt install python3-pip -y")
            ssh_command(line[0], f"pip install -r {requirements_path}")

            logger.success(f"Installed requirements to {line[0]}")


def install_memcached_and_docker():
    for line in get_node_info():
        if line[0].startswith(MEMCACHED):

            source_path = "./scripts/install_docker.sh"
            destination_path = "~/install_docker.sh"

            copy_file_to_node(line[0], source_path, destination_path)
            ssh_command(line[0], "sudo bash ~/install_docker.sh")

            ssh_command(line[0], sudo_command)

            # brutzel brutzel tsch tsch
            time.sleep(5)

            logger.info(f"Installed docker to {line[0]}")

            memcached_ip = get_node_ip(MEMCACHED)
            if memcached_ip is None:
                print("Could not find the IP of the memcache server")
                sys.exit(1)

            ssh_command(line[0], "sudo apt update")
            ssh_command(line[0], "sudo apt install -y memcached libmemcached-tools")

            # copy only once, to use as a starting point
            with open("scripts/memcached.conf", "r") as f:
                content = (
                    f.read()
                    .replace("MEMCACHED_INTERNAL_IP", memcached_ip)
                    .replace("MEMORY_LIMIT", "1024")
                    .replace("NUM_THREADS", f"{NUM_THREADS_MEMCACHED}")
                )
            with tempfile.NamedTemporaryFile(mode="w") as temp_file:
                temp_file.write(content)
                copy_file_to_node(line[0], temp_file.name, "~/memcached.conf")

            ssh_command(line[0], "sudo mv ~/memcached.conf /etc/memcached.conf")
            ssh_command(line[0], "sudo systemctl restart memcached")

            logger.success(f"Installed memcached to {line[0]}")


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
    memcached_ip = get_node_ip(MEMCACHED)

    if client_agent_name is None or client_measure_name is None or memcached_ip is None:
        print("Could not find client-agent-name, client-measure, or memcached node")
        sys.exit(1)

    mcperf_agent_command = "./memcache-perf-dynamic/mcperf -T 16 -A"
    log_agent_file = open(os.path.join(LOG_RESULTS, "mcperf_agent.txt"), "w")
    ssh_command(client_agent_name, mcperf_agent_command, is_async=True, file=log_agent_file)  # type: ignore

    mc_perf_measure_command = f"./memcache-perf-dynamic/mcperf -s {memcached_ip} --loadonly && ./memcache-perf-dynamic/mcperf -s {memcached_ip} -a {client_agent_ip} --noload -T 16 -C 4 -D 4 -Q 1000 -c 4 -t 1800 --qps_interval 10 --qps_min 5000 --qps_max 100000"
    log_file = open(os.path.join(LOG_RESULTS, "mcperf.txt"), "w")
    ssh_command(client_measure_name, mc_perf_measure_command, is_async=True, file=log_file)  # type: ignore


if __name__ == "__main__":
    task4()
