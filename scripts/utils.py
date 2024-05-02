import os
import subprocess
import sys
from typing import Optional
from enum import Enum

from loguru import logger


#### SETUP ENVIRONMENT VARIABLES ########

KOPS_STATE_STORE = "gs://cca-eth-2024-group-076-djueni/"
PROJECT = "gcloud config get-value project"
env = dict(os.environ.copy())
env["KOPS_STATE_STORE"] = KOPS_STATE_STORE
env["PROJECT"] = PROJECT
env["ZONE"] = "europe-west3-a"
env["USER"] = "ubuntu"

# if os is not windows
if os.name != "nt":
    assert (
        "cca-eth" in subprocess.run("gcloud config get-value project".split(), capture_output=True).stdout.decode()
    ), "You are not in the correct project. Run 'gcloud config set project cca-eth-2024-group-076-djueni'"

#### END SETUP ENVIRONMENT VARIABLES ####


def run_command(command: list[str], env: dict[str, str] = env, log_success: bool = True) -> subprocess.CompletedProcess[bytes]:
    res = subprocess.run(command, env=env, capture_output=True)
    if res.returncode != 0:
        logger.error(f"\nCommand: {' '.join(command)}")
        print(f"Output: {res.stderr.decode('utf-8')}")
        return res

    if log_success:
        logger.success(f"\nCommand: {' '.join(command)}")
        print(f"Output: {res.stdout.decode('utf-8')}")
    return res


def ssh_command(
    node: str,
    command: str,
    env: dict[str, str] = env,
    is_async: bool = False,
    file=None
) -> subprocess.CompletedProcess[bytes] | subprocess.Popen[bytes]:
    ssh_command = [
        "gcloud",
        "compute",
        "ssh",
        "--zone",
        env.get("ZONE", "europe-west3-a"),
        "--ssh-key-file",
        os.path.expanduser("~/.ssh/cloud-computing"),
        f"{env.get('USER', 'ubuntu')}@{node}",
        "--command",
        command,
    ]
    logger.info(f"\n({'Asynchronous' if is_async else 'Synchronous'}) SSH Command on node {node}: {command}")

    if is_async:
        return subprocess.Popen(ssh_command, env=env, stdout=file, stderr=subprocess.STDOUT)
    else:
        return run_command(ssh_command, env, log_success=False)


class Part(Enum):
    PART1 = "part1"
    PART2A = "part2a"
    PART2B = "part2b"
    PART3 = "part3"
    PART4 = "part4"

    @property
    def yaml_file(self) -> str:
        return f"{self.value}.yaml"

    @property
    def cluster_name(self) -> str:
        return f"{self.value}.k8s.local"


def start_cluster(part: Part) -> None:
    """
    Start a kubernetes cluster using kops
    """
    logger.info(f"########### Starting cluster for {part} ###########")

    yaml_file = part.yaml_file
    cluster_name = part.cluster_name

    create_bucket_command = ["gsutil", "mb", KOPS_STATE_STORE]
    run_command(create_bucket_command, env)

    create_command = ["kops", "create", "-f", yaml_file]
    run_command(create_command, env)

    create_secret_command = [
        "kops",
        "create",
        "secret",
        "--name",
        cluster_name,
        "sshpublickey",
        "admin",
        "-i",
        os.path.expanduser("~/.ssh/cloud-computing.pub"),
    ]
    run_command(create_secret_command, env)

    update_command = ["kops", "update", "cluster", "--name", cluster_name, "--yes", "--admin"]
    run_command(update_command, env)

    logger.info("Waiting for cluster to be ready... (~10min)")
    validate_command = ["kops", "validate", "cluster", "--wait", "10m"]
    run_command(validate_command, env)

    logger.success("Cluster is ready.")
    view_command = ["kubectl", "get", "nodes", "-o", "wide"]
    run_command(view_command, env)
    logger.info(
        "In order to ssh into one of the nodes, use:\n'gcloud compute ssh --ssh-key-file ~/.ssh/cloud-computing ubuntu@<MACHINE_NAME> --zone europe-west3-a'"
    )


def delete_cluster(cluster_name: str) -> None:
    # We create a copy of the current environment variables to make sure we don't modify the original
    environment_dict = dict(os.environ)

    # Update the environment variables
    environment_dict["KOPS_STATE_STORE"] = KOPS_STATE_STORE
    environment_dict["PROJECT"] = PROJECT

    delete_comand = ["kops", "delete", "cluster", cluster_name, "--yes"]
    run_command(delete_comand, environment_dict)

    delete_bucket_command = ["gsutil", "rm", "-r", KOPS_STATE_STORE]
    run_command(delete_bucket_command, environment_dict)

    logger.success("########### Cluster deleted ###########")


def get_info(resource_type: str) -> list[list[str]]:
    get_command = ["kubectl", "get", resource_type, "-o", "wide"]
    res = subprocess.run(get_command, env=dict(os.environ), capture_output=True)

    print(res.stdout.decode("utf-8"))

    # Split the output into lines and remove the first line (header)
    lines = res.stdout.decode("utf-8").split("\n")[1:]

    # Split each line into a list of strings and remove empty lines and empty strings
    info = [line.split(" ") for line in lines if line != ""]
    info = [[s for s in line if s != ""] for line in info]
    return info


def get_node_info(d: Optional[dict] = None) -> list[list[str]]:
    # Return: [ [node_name, status, roles, age, version, internal_ip, external_ip], ... ]
    info = get_info("nodes")

    if d is None:
        d = {}

    for line in info:
        d[line[0][:-5]] = {
            "node_name": line[0],
            "status": line[1],
            "roles": line[2],
            "age": line[3],
            "version": line[4],
            "internal_ip": line[5],
            "external_ip": line[6],
        }
    return info


def get_pods_info() -> list[list[str]]:
    # Return: [ [name, ready, status, restarts, age, ip, node], ... ]
    return get_info("pods")


def get_jobs_info() -> list[list[str]]:
    # Return: [ [name, completions, age], ... ]
    return get_info("jobs")


def pods_ready() -> bool:
    info = get_pods_info()
    if len(info) == 0:
        return False
    for pod in info:
        logger.info(pod)
        if pod[1] != "1/1" or pod[2] != "Running":
            return False
    return True


def services_ready() -> bool:
    info = get_info("services")
    if len(info) == 0:
        return False
    for service in info:
        logger.info(service)
        if service[3] == "<pending>":
            return False
    return True


def pods_completed(job_name=None) -> bool:
    info = get_pods_info()
    if len(info) == 0:
        return False
    if job_name is not None:
        info = [pod for pod in info if job_name in pod[0]]
    for pod in info:
        if "memcached" in pod[0]:
            continue
        if pod[2] != "Completed" and pod[2] != "Error":
            return False
    return True


def jobs_ready() -> bool:
    info = get_jobs_info()

    if len(info) == 0:
        return False

    for line in info:
        if line[1] != "1/1":
            return False
    return True


def copy_file_to_node(node: str, source_path: str, destination_path: str) -> None:

    print(f"Copying file {source_path} to node {node}")

    copy_command = [
        "gcloud",
        "compute",
        "scp",
        "--ssh-key-file",
        os.path.expanduser("~/.ssh/cloud-computing"),
        "--zone",
        "europe-west3-a",
        source_path,
        f"ubuntu@{node}:{destination_path}",
    ]
    run_command(copy_command, dict(os.environ))


def check_output(res: subprocess.CompletedProcess) -> None:
    if res.returncode != 0:
        print(res.stderr.decode("utf-8"))
        sys.exit(1)


def log_pods() -> None:
    for info in get_pods_info():
        name = info[0]
        res = subprocess.run(["kubectl", "logs", name], capture_output=True)
        info = res.stdout.decode("utf-8")
        logger.info(f"Logs for pod {name}\n\n####LOGS#### {str(info)}\n####END LOGS####\n\n")
        error = res.stderr.decode("utf-8")
        if error:
            logger.error(f"Error for pod {name}\n\n####ERROR#### {str(error)}\n####END ERROR####\n\n")


def get_node_ip(node_name: str) -> Optional[str]:
    info = get_node_info()
    for line in info:
        if line[0].startswith(node_name):
            return line[5]
    return None


def get_pod_ip(pod_name: str) -> Optional[str]:
    info = get_pods_info()
    for line in info:
        if pod_name in line[0]:
            return line[5]

    return None
