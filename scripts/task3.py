from time import sleep
import subprocess
import click
import time
import os
import yaml
import tempfile

from loguru import logger

from scripts.utils import (
    Part,
    pods_completed,
    scp_command,
    ssh_command,
    start_cluster,
    run_command,
    pods_ready,
    get_node_info,
    get_pods_info,
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
        start_memcached(env)
        logger.info("Memcached started")
        start_mcperf(env)
        logger.info("mcperf started")
        schedule_batch_jobs(env)
        logger.info("Batch jobs scheduled")
        # wait for jobs to finish
        while not pods_completed():
            sleep(5)
        # log_pods(env)
        log_time()

    except Exception as e:
        logger.error(e)
    finally:
        # cleanup
        for process in PROCESSES:
            process.kill()
        run_command("kubectl delete jobs --all".split())
        run_command("kubectl delete pods --all".split())


def log_time():
    get_command = "kubectl get pods -o json > results.json"
    os.system(get_command)
    get_command = f"python3 get_time.py results.json > {os.path.join(LOG_RESULTS, 'execution_time.txt')}"
    os.system(get_command)


def start_memcached(env: dict = env) -> None:
    # Start memcached pod using `kubectl create -f memcached.yaml`
    path = os.path.join(".", "memcache-t1-cpuset-part3.yaml")
    # TODO : is sync?
    run_command(f"kubectl create -f {path}".split())


def schedule_batch_jobs(env: dict) -> None:
    # blackscholes,canneal,dedup,ferret,freqmine,radix,vips
    schedule_single_job("blackscholes", "blackscholes", "node-c-8core", "4,5", 2)  # fourth
    schedule_single_job("canneal", "canneal", "node-b-4core", "2,3", 2)  # fifth
    schedule_single_job("radix", "radix", "node-c-8core", "6,7", 2, benchmark_suite="splash2x")  # first
    schedule_single_job("ferret", "ferret", "node-b-4core", "0,1,2", 3)  # seventh (almost 6th)
    schedule_single_job("freqmine", "freqmine", "node-c-8core", "0,1,2,3,4,6,7", 6)  # sixth
    schedule_single_job("dedup", "dedup", "node-a-2core", "1", 1)  # second
    schedule_single_job("vips", "vips", "node-c-8core", "0,1", 2)  # third


def schedule_single_job(
    job_name: str, benchmark: str, node_selector: str, cores: str, nr_threads: int, benchmark_suite="parsec"
) -> None:
    # Start a single job using `kubectl create -f batch-job.yaml`
    file = modified_yaml_file(
        os.path.join(PARSEC_PATH, f"parsec-{job_name}.yaml"),
        selector=__node_selector(node_selector),
        container_args=__container_args(cores, benchmark, nr_threads, benchmark_suite),
    )
    run_command(f"kubectl create -f {file.name}".split())
    file.close()


def get_node_ip(node_name: str, env: dict = env) -> str:
    info = get_node_info()
    for line in info:
        print(line)
        if line[0].startswith(node_name):
            return line[5]


def get_pod_ip(pod_name: str, env: dict = env) -> str:
    info = get_pods_info()
    for line in info:
        if "memcached" in line[0]:
            return line[5]


def is_memcached_ready(env: dict = env) -> bool:
    return pods_ready()


def log_pods(env: dict = env) -> None:
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


def start_mcperf(env: dict) -> None:
    # Start mcperf pod(s) using `kubectl create -f mcperf.yaml`
    # use make_mcperf.sh script to build mcperf on client-agent and client-measure
    global PROCESSES
    for _ in range(10):
        if is_memcached_ready():
            break
        time.sleep(2)
    assert is_memcached_ready(), "Memcached pod not ready"
    d = {}
    for line in get_node_info(d):
        if line[0].startswith("client-agent-") or line[0].startswith("client-measure-"):
            # copy make_mcperf.sh to the node
            node = line[0]
            logger.info(f"Copying mcperf files to {line[0]}")
            res = scp_command(
                "./scripts/install_mcperf.sh",  # local file
                "~/install_mcperf.sh",  # remote file
                node,
            )
            # run make_mcperf.sh on the node
            res = ssh_command(node, "chmod +x ~/install_mcperf.sh && ~/install_mcperf.sh")
            #
            ssh_command(node, "ls -al")
            if node.startswith("client-agent-a"):
                res = ssh_command(
                    node,
                    "~/memcache-perf-dynamic/mcperf -T 2 -A",
                    is_async=True,
                )
            elif node.startswith("client-agent-b"):
                log_file = open(os.path.join(LOG_RESULTS, "mcperf-agent-b.txt"), "w")
                error_file = open(os.path.join(LOG_RESULTS, "mcperf-agent-b.error"), "w")
                res = ssh_command(
                    node,
                    "~/memcache-perf-dynamic/mcperf -T 4 -A",
                    is_async=True,
                    stdout=log_file,
                    stderr=error_file,
                )
                PROCESSES.append(res)

            elif node.startswith("client-measure"):
                MEMCACHED_IP = get_pod_ip("memcached")
                INTERNAL_AGENT_A_IP = get_node_ip("client-agent-a")
                INTERNAL_AGENT_B_IP = get_node_ip("client-agent-b")
                log_file = open(os.path.join(LOG_RESULTS, "mcperf-loadonly.txt"), "w")
                error_file = open(os.path.join(LOG_RESULTS, "mcperf-loadonly.error"), "w")
                res = ssh_command(
                    node,
                    f"~/memcache-perf-dynamic/mcperf -s {MEMCACHED_IP} --loadonly",
                    is_async=True,
                    stdout=log_file,
                    stderr=error_file,
                )
                PROCESSES.append(res)
                log_file = open(os.path.join(LOG_RESULTS, "mcperf.txt"), "w")
                error_file = open(os.path.join(LOG_RESULTS, "mcperf.error"), "w")
                res = ssh_command(
                    node,
                    f"~/memcache-perf-dynamic/mcperf -s {MEMCACHED_IP} -a {INTERNAL_AGENT_A_IP} -a {INTERNAL_AGENT_B_IP} \
                    --noload -T 6 -C 4 -D 4 -Q 1000 -c 4 -t 10 --scan 30000:30500:5",
                    is_async=True,
                    stdout=log_file,
                    stderr=error_file,
                )
                PROCESSES.append(res)


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
