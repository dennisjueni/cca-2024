import time
import click
import sys
import os
from loguru import logger


# add scripts to sys path
try:
    sys.path.append("scripts")
except Exception as e:
    print(e)


from utils import *
from task4_config import *


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
        install_mcperf(False)

        memcached_name = None
        for line in get_node_info():
            if line[0].startswith(MEMCACHED):
                memcached_name = line[0]
        if memcached_name is None:
            logger.error("Could not find the memcached node")
            sys.exit(1)

        copy_task4(["task4_cpu.py"])

        num_thread_candidates = [1, 2]
        cores_candidates = [[1], [1, 2]]

        base_log_dir = os.path.join(".", "results-part4", "part1", time.strftime("%Y-%m-%d-%H-%M"))
        os.makedirs(base_log_dir, exist_ok=True)
        ssh_command(memcached_name, "lscpu > ~/lscpu.txt")
        copy_file_from_node(memcached_name, "~/lscpu.txt", os.path.join(base_log_dir, "lscpu.txt"))

        for num_threads in num_thread_candidates:

            install_memcached(num_threads=num_threads)

            for cores in cores_candidates:
                # We will run each of the threads-core-configuration 3 times
                print("Running with", len(cores), "cores and", num_threads, "threads")
                for i in range(3):

                    ssh_command(memcached_name, "sudo systemctl restart memcached")
                    time.sleep(10)

                    log_results = os.path.join(
                        base_log_dir,
                        f"{len(cores)}C_{num_threads}T",
                        f"run_{i}",
                    )
                    os.makedirs(log_results, exist_ok=True)

                    cpu_file = open(os.path.join(log_results, "cpu_utils.txt"), "w")
                    ssh_command(memcached_name, "taskset -c 3 python3 ~/task4_cpu.py", is_async=True, file=cpu_file)  # type: ignore

                    taskset_command = f"sudo taskset -a -cp {','.join(list(map(str, cores)))} $(pgrep memcached)"
                    ssh_command(memcached_name, taskset_command)

                    time.sleep(10)

                    ssh_command(memcached_name, "sudo systemctl status memcached")

                    agent_command = "./memcache-perf-dynamic/mcperf -T 16 -A"
                    measure_command = "./memcache-perf-dynamic/mcperf -s MEMCACHED_IP --loadonly && ./memcache-perf-dynamic/mcperf -s MEMCACHED_IP -a AGENT_IP --noload -T 16 -C 4 -D 4 -Q 1000 -c 4 -t 5 --scan 5000:125000:5000"

                    start_mcperf(agent_command=agent_command, measure_command=measure_command, log_results=log_results)

                    time.sleep(200)

    finally:
        print("Part 1 done")


def run_part2():
    memcached_name = None
    for line in get_node_info():
        if line[0].startswith(MEMCACHED):
            memcached_name = line[0]
            break
    if memcached_name is None:
        logger.error("Could not find the memcached node")
        sys.exit(1)

    base_log_dir = os.path.join(".", "results-part4", "part2_final_runs", time.strftime("%Y-%m-%d-%H-%M"))
    os.makedirs(base_log_dir, exist_ok=True)

    try:
        copy_task4(["task4_controller.py", "task4_scheduler_logger.py", "task4_job.py", "task4_config.py"])
        install_memcached(num_threads=2)
        install_docker()

        for docker_image in DOCKERIMAGES.values():
            ssh_command(memcached_name, f"sudo docker pull {docker_image}")

        install_mcperf(False)

        mcperf_time = 900

        agent_command = "./memcache-perf-dynamic/mcperf -T 16 -A"
        measure_command = f"./memcache-perf-dynamic/mcperf -s MEMCACHED_IP --loadonly && ./memcache-perf-dynamic/mcperf -s MEMCACHED_IP -a AGENT_IP --noload -T 16 -C 4 -D 4 -Q 1000 -c 4 -t {mcperf_time} --qps_interval 10 --qps_min 5000 --qps_max 100000 --qps_seed 3274"

        start_mcperf(agent_command=agent_command, measure_command=measure_command, log_results=base_log_dir)
        start_time = time.time()

        time.sleep(5)

        start_memcached_controller()

        # After mcperf_time seconds, the memcached controller should be finished and additionally the mcperf command should have finished as well
        while True:
            time.sleep(10)
            if time.time() - start_time > mcperf_time + 10:
                break
            logger.info(f"{mcperf_time - (time.time() - start_time)} seconds remaining")

        res = ssh_command(memcached_name, "ls")
        files = res.stdout.decode("utf-8").split("\n")  # type: ignore
        files = [f for f in files if f.startswith("log") and f.endswith(".txt")]
        for f in files:
            copy_file_from_node(memcached_name, f"~/{f}", os.path.join(base_log_dir, "log.txt"))

    finally:
        stop_comand = "sudo docker stop $(docker ps -a -q)"
        remove_command = "sudo docker rm -f $(docker ps -a -q)"
        for line in get_node_info():
            if line[0].startswith(MEMCACHED):
                ssh_command(line[0], stop_comand)
                ssh_command(line[0], remove_command)
                ssh_command(line[0], "sudo rm log*.txt")
            if line[0].startswith("client-agent") or line[0].startswith("client-measure"):
                ssh_command(line[0], "sudo pkill mcperf")


def start_memcached_controller():
    logger.info("########### Starting Memcached Controller ###########")
    node_info = get_node_info()
    memcached_name = None

    for line in node_info:
        if line[0].startswith(MEMCACHED):
            memcached_name = line[0]

    memcached_ip = get_node_ip(MEMCACHED)

    if memcached_name is None or memcached_ip is None:
        logger.error("Could not find the controller node")
        sys.exit(1)

    ssh_command(memcached_name, f"taskset -c 2,3 python3 ~/task4_controller.py {memcached_ip}")

    logger.success(f"Finished running memcached controller on {memcached_name}")


def copy_task4(files: list[str]):
    requirements_file_name = "requirements_part4.txt"

    source_folder = os.path.join(".", "scripts")
    destination = os.path.join("~")

    for line in get_node_info():
        if line[0].startswith(MEMCACHED):
            for file_name in files:
                source_file = os.path.join(source_folder, file_name)
                copy_file_to_node(line[0], source_file, destination)

            requirements_file = os.path.join(source_folder, requirements_file_name)
            copy_file_to_node(line[0], requirements_file, destination)

            logger.info(f"Copied python scripts to {line[0]}")

            ssh_command(line[0], f"sudo apt install python3-pip -y")
            ssh_command(line[0], f"pip install -r {requirements_file_name}")

            logger.success(f"Installed requirements to {line[0]}")


def install_docker():
    for line in get_node_info():
        if line[0].startswith(MEMCACHED):
            source_path = "./scripts/install_docker.sh"
            destination_path = "~/install_docker.sh"

            copy_file_to_node(line[0], source_path, destination_path)
            ssh_command(line[0], "sudo bash ~/install_docker.sh")

            ssh_command(line[0], f"sudo usermod -a -G docker ubuntu")

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
            with open("./scripts/memcached.conf", "r") as f:
                content = (
                    f.read()
                    .replace("MEMCACHED_INTERNAL_IP", memcached_ip)
                    .replace("MEMORY_LIMIT", "1024")
                    .replace("NUM_THREADS", f"{num_threads}")
                )
                ssh_command(line[0], f'sudo printf "{content}" > ~/memcached.conf')

            ssh_command(line[0], "sudo mv ~/memcached.conf /etc/memcached.conf")
            ssh_command(line[0], "sudo systemctl restart memcached")

            time.sleep(10)

            logger.success(f"Installed memcached to {line[0]}")


def start_mcperf(agent_command: str, measure_command: str, log_results: str):
    logger.info("########### Starting Mcperf on all 2 machines ###########")
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

    log_agent_file = open(os.path.join(log_results, "mcperf_agent.txt"), "w")
    ssh_command(client_agent_name, agent_command, is_async=True, file=log_agent_file)  # type: ignore

    measure_command = measure_command.replace("MEMCACHED_IP", memcached_ip).replace("AGENT_IP", client_agent_ip)

    log_file = open(os.path.join(log_results, "mcperf.txt"), "w")
    ssh_command(client_measure_name, measure_command, is_async=True, file=log_file)  # type: ignore


if __name__ == "__main__":
    task4()
