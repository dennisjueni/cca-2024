import os
import subprocess
import sys
from typing import Optional
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


def run_command(command: list[str], env: dict[str, str] = env) -> subprocess.CompletedProcess[bytes]:
    res = subprocess.run(command, env=env, capture_output=True)
    if res.returncode != 0:
        print("\033[91m!!! ERROR OCCURED !!!\033[0m")  # Print in red
        print(res.stderr.decode("utf-8"))

    print(res.stdout.decode("utf-8"))
    return res


def scp_command(
    source_path: str, destination_path: str, node: str, env: dict[str, str] = env
) -> subprocess.CompletedProcess[bytes]:
    command = [
        "gcloud",
        "compute",
        "scp",
        "--ssh-key-file",
        os.path.expanduser("~/.ssh/cloud-computing"),
        "--zone",
        env.get("ZONE", "europe-west3-a"),
        source_path,
        f"{env.get('USER', 'ubuntu')}@{node}:{destination_path}",
    ]
    return run_command(command, env)


def ssh_command(node: str, command: str, env: dict[str, str] = env) -> subprocess.CompletedProcess[bytes]:
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
    return run_command(ssh_command, env)


def start_cluster(yaml_file: str, cluster_name: str, env=env) -> None:
    """
    yaml_file: str - path to the yaml file that describes the cluster, e.g. "part3.yaml"
    cluster_name: str - name of the cluster, e.g. "cca-eth-2024-group-076-djueni.k8s.local"
    """
    print("########### Starting cluster ###########")

    # We create a copy of the current environment variables to make sure we don't modify the original

    with open(yaml_file, "r") as f:
        yaml = f.read()
        assert cluster_name in yaml, f"Cluster name {cluster_name} not found in yaml file"

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

    logger.info("Cluster is ready.")
    view_command = ["kops", "get", "nodes", "-o", "wide"]
    run_command(view_command, env)
    print(
        "In order to ssh into one of the nodes, use:\n'gcloud compute ssh --ssh-key-file ~/.ssh/cloud-computing ubuntu@<MACHINE_NAME> --zone europe-west3-a'"
    )

    print("########### Cluster started ###########")
    return env


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

    print("########### Cluster deleted ###########")


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
    if d is not None:
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
        if pod[1] != "1/1" or pod[2] != "Running":
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
