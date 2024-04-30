import sys
import subprocess
import click
import time
import os
import yaml
import tempfile
from time import sleep
from typing import Optional

from loguru import logger

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
)


class Job:
    def __init__(
        self,
        job_name: str,
        benchmark: str,
        node_selector: str,
        cores: str,
        nr_threads: int,
        benchmark_suite="parsec",
        depends_on=[],
    ):
        self.job_name = job_name
        self.benchmark = benchmark
        self.node_selector = node_selector
        self.cores = cores
        self.nr_threads = nr_threads
        self.benchmark_suite = benchmark_suite
        self.depends_on = depends_on
        self.file = self._create_file()
        self.is_finished_prop = False
        self.started = False

    def _create_file(self):
        return modified_yaml_file(
            os.path.join(PARSEC_PATH, f"parsec-{self.job_name}.yaml"),
            selector=__node_selector(self.node_selector),
            container_args=__container_args(
                self.cores, self.benchmark, self.nr_threads, benchmark_suite=self.benchmark_suite
            ),
        )

    @property
    def is_finished(self):
        self.is_finished_prop = self.is_finished_prop or pods_completed(self.job_name)
        return self.is_finished_prop

    def start(self):
        if self.started:
            return
        for job in self.depends_on:
            if not job.is_finished:
                logger.info(f"{self.job_name} is waiting for {job.job_name} to finish. Try again later.")
                return
        run_command(f"kubectl create -f {self.file.name}".split())
        self.started = True
        logger.info(f"Started job {self.job_name}")
        self.file.close()


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
        # log_file.flush()
        # error_file.flush()
        # sleep(5)
        for process in PROCESSES:
            process.kill()
        # sleep(5)
        # log_file.close()
        # error_file.close()
        # cleanup

        # log_pods()

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
            logger.info(f"Copyied the mcperf install script to {line[0]}")

            install_command = f"chmod +x {destination_path} && {destination_path}"
            ssh_command(
                line[0],
                install_command,
                is_async=False,
            )

    logger.success("########### Finished Installing mcperf on all 3 machines ###########")


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
        stdout=log_file,
        stderr=error_file,
    )
    PROCESSES.append(res)

    return log_file, error_file


def schedule_batch_jobs() -> None:
    # blackscholes,canneal,dedup,ferret,freqmine,radix,vips

    # schedule_single_job("blackscholes", "blackscholes", "node-c-8core", "4,5", 2)  # fourth
    # schedule_single_job("canneal", "canneal", "node-b-4core", "2,3", 2)  # fifth
    # schedule_single_job("radix", "radix", "node-c-8core", "6,7", 2, benchmark_suite="splash2x")  # first
    # schedule_single_job("ferret", "ferret", "node-b-4core", "0,1,2", 3)  # seventh (almost 6th)
    # schedule_single_job("freqmine", "freqmine", "node-c-8core", "0,1,2,3,4,6,7", 6)  # sixth
    # schedule_single_job("dedup", "dedup", "node-a-2core", "1", 1)  # second
    # schedule_single_job("vips", "vips", "node-c-8core", "0,1", 2)  # third

    # TODO : Please Check if depends_on makes sense and works :-)
    ferret_job = Job("ferret", "ferret", "node-b-4core", "0,1,2,3", 4)
    radix_job = Job("radix", "radix", "node-b-4core", "2,3", 2, benchmark_suite="splash2x")
    vips_job = Job("vips", "vips", "node-b-4core", "2,3", 2, depends_on=[radix_job])
    freqmine_job = Job("freqmine", "freqmine", "node-b-4core", "0,1,2,3", 8)
    blackscholes_job = Job("blackscholes", "blackscholes", "node-c-8core", "4,5", 2)
    canneal_job = Job("canneal", "canneal", "node-c-8core", "6,7", 2)
    dedup_job = Job("dedup", "dedup", "node-a-2core", "1", 1)
    jobs = [blackscholes_job, canneal_job, dedup_job, ferret_job, freqmine_job, radix_job, vips_job]

    while True:
        unstarted_jobs = [job for job in jobs if not job.started]
        if len(unstarted_jobs) == 0:
            break
        for job in unstarted_jobs:
            job.start()
        sleep(2)


def get_node_ip(node_name: str) -> Optional[str]:
    info = get_node_info()
    for line in info:
        print(line)
        if line[0].startswith(node_name):
            return line[5]
    return None


def get_pod_ip(pod_name: str) -> Optional[str]:
    info = get_pods_info()
    for line in info:
        if "memcached" in line[0]:
            return line[5]

    return None


def is_memcached_ready() -> bool:
    return pods_ready()


def log_pods() -> None:
    for info in get_pods_info():
        name = info[0]
        res = subprocess.run(["kubectl", "logs", name], capture_output=True)
        info = res.stdout.decode("utf-8")
        logger.info(f"Logs for pod {name}\n\n####LOGS#### {str(info)}\n####END LOGS####\n\n")
        error = res.stderr.decode("utf-8")
        if error:
            logger.error(f"Error for pod {name}\n\n####ERROR#### {str(error)}\n####END ERROR####\n\n")


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


def log_time():
    get_command = "kubectl get pods -o json > results.json"
    os.system(get_command)
    get_command = f"python3 get_time.py results.json > {os.path.join(LOG_RESULTS, 'execution_time.txt')}"
    os.system(get_command)


def __taskset_command(cores: str, benchmark_name: str, nr_threads: int, benchmark_suite="parsec") -> list:
    # args: ["-c", "taskset -c 4,5,6 ./run -a run -S parsec -p canneal -i native -n 3"]
    return [
        "-c",
        f"taskset -c {cores} ./run -a run -S {benchmark_suite} -p {benchmark_name} -i native -n {nr_threads}",
    ]


def __container_args(cores: str, benchmark: str, nr_threads: int, benchmark_suite="parsec") -> tuple:
    return ["spec", "template", "spec", "containers", 0, "args"], __taskset_command(
        cores, benchmark, nr_threads, benchmark_suite=benchmark_suite
    )


def __node_selector(selector_value: str) -> tuple:
    return ["spec", "template", "spec", "nodeSelector", "cca-project-nodetype"], selector_value


####### TESTS #######

PARSEC_PATH = os.path.join(".", "parsec-benchmarks", "part3")

if __name__ == "__main__":
    task3()
    # file = modified_yaml_file(
    #     os.path.join(PARSEC_PATH, "parsec-blackscholes.yaml"),
    #     selector=__node_selector("node-b-4core"),
    #     container_args=__container_args("4,5,6,7", "blackscholes", 3),
    # )
    # subprocess.run(["cat", file.name])
    # file.close()
