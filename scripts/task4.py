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


@click.command()
@click.option(
    "--start", "-s", help="Flag indicating if the cluster should be started", is_flag=True, default=False, type=bool
)
@click.option(
    "--part", "-p", help="Flag indicating which subpart of part 4 should be run", is_flag=False, default=1, type=int
)
def task4(start: bool, part: int):

    if start:
        start_cluster(part=Part.PART4)

    if part == 1:
        run_part1()
    elif part == 2:
        run_part2()


def run_part1():
    try:
        # We do not need most of it however it is easier to just copy everything
        copy_task4()

        install_mcperf(False)

        memcached_name = None
        for line in get_node_info():
            if line[0].startswith(MEMCACHED):
                memcached_name = line[0]
        if memcached_name is None:
            logger.error("Could not find the memcached node")
            sys.exit(1)

        thread_candidates = [1, 2]
        cores_candidates = [[0], [0, 1]]

        base_log_dir = os.path.join(".", "results-part4", "part1", time.strftime("%Y-%m-%d-%H-%M"))

        for num_threads in thread_candidates:
            for cores in cores_candidates:
                # We will run each of the threads-core-configuration 3 times
                for i in range(3):

                    install_memcached(num_threads=num_threads)

                    taskset_command = f"sudo taskset -acp {','.join(list(map(str, cores)))} $(pgrep memcached)"
                    ssh_command(memcached_name, taskset_command)

                    agent_command = "./memcache-perf-dynamic/mcperf -T 16 -A"
                    measure_command = "./memcache-perf-dynamic/mcperf -s MEMCACHED_IP --loadonly && ./memcache-perf-dynamic/mcperf -s MEMCACHED_IP -a AGENT_IP --noload -T 16 -C 4 -D 4 -Q 1000 -c 4 -t 5 --scan 5000:125000:5000"

                    log_results = os.path.join(
                        base_log_dir,
                        f"{len(cores)}C_{num_threads}T",
                        f"run_{i}",
                    )
                    os.makedirs(log_results, exist_ok=True)
                    start_mcperf(agent_command=agent_command, measure_command=measure_command, log_results=log_results)

                    # We will only need this for part 1d!
                    # cpu_file = open(os.path.join(log_results, "cpu_utils.txt"), "w")
                    # ssh_command(memcached_name, "python3 ~/task4_cpu.py", is_async=True, file=cpu_file)  # type: ignore

                    # This is a bit too much, but after 40*5 = 200 seconds we should be done
                    time.sleep(210)

    finally:
        print("Part 1 done")


def run_part2():
    try:
        os.makedirs(LOG_RESULTS, exist_ok=True)
        copy_task4()
        install_memcached(num_threads=2)
        install_docker()

        install_mcperf(False)  # install dynamic mcperf on agent and measure

        agent_command = "./memcache-perf-dynamic/mcperf -T 16 -A"
        measure_command = "./memcache-perf-dynamic/mcperf -s MEMCACHED_IP --loadonly && ./memcache-perf-dynamic/mcperf -s MEMCACHED_IP -a AGENT_IP --noload -T 16 -C 4 -D 4 -Q 1000 -c 4 -t 1000 --qps_interval 10 --qps_min 5000 --qps_max 100000"

        start_mcperf(agent_command=agent_command, measure_command=measure_command)

        time.sleep(20)

        start_memcached_controller()

        # A safety to wait for mcperf to finish
        time.sleep(1000)
    finally:
        stop_comand = "sudo docker stop $(docker ps -a -q)"
        remove_command = "sudo docker rm -f $(docker ps -a -q)"
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


def install_docker():
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


def install_memcached(num_threads: int):
    for line in get_node_info():
        if line[0].startswith(MEMCACHED):

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
                    .replace("NUM_THREADS", f"{num_threads}")
                )
            with tempfile.NamedTemporaryFile(mode="w") as temp_file:
                temp_file.write(content)
                copy_file_to_node(line[0], temp_file.name, "~/memcached.conf")

            ssh_command(line[0], "sudo mv ~/memcached.conf /etc/memcached.conf")
            ssh_command(line[0], "sudo systemctl restart memcached")

            logger.success(f"Installed memcached to {line[0]}")


def start_mcperf(agent_command: str, measure_command: str, log_results: str = LOG_RESULTS):
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

    if client_agent_name is None or client_measure_name is None or memcached_ip is None or client_agent_ip is None:
        print("Could not find client-agent-name, client-measure, or memcached node")
        sys.exit(1)

    # make sure that no instance of mcperf is running
    ssh_command(client_measure_name, "sudo pkill mcperf")
    ssh_command(client_agent_name, "sudo pkill mcperf")

    log_agent_file = open(os.path.join(log_results, "mcperf_agent.txt"), "w")
    ssh_command(client_agent_name, agent_command, is_async=True, file=log_agent_file)  # type: ignore

    measure_command = measure_command.replace("MEMCACHED_IP", memcached_ip).replace("AGENT_IP", client_agent_ip)

    log_file = open(os.path.join(log_results, "mcperf.txt"), "w")
    ssh_command(client_measure_name, measure_command, is_async=True, file=log_file)  # type: ignore


if __name__ == "__main__":
    task4()
