import os
import subprocess
import sys

KOPS_STATE_STORE = "gs://cca-eth-2024-group-076-djueni/"
PROJECT = "gcloud config get-value project"

# if os is not windows
if os.name != "nt":
    assert (
        "cca-eth" in subprocess.run("gcloud config get-value project".split(), capture_output=True).stdout.decode()
    ), "You are not in the correct project. Run 'gcloud config set project cca-eth-2024-group-076-djueni'"


def run_command(command: list[str], env: dict[str, str] = dict(os.environ)) -> None:
    res = subprocess.run(command, env=env, capture_output=True)
    if res.returncode != 0:
        print("\033[91m!!! ERROR OCCURED !!!\033[0m")  # Print in red
        print(res.stderr.decode("utf-8"))

    print(res.stdout.decode("utf-8"))


def start_cluster(yaml_file: str, cluster_name: str) -> None:
    print("########### Starting cluster ###########")

    # We create a copy of the current environment variables to make sure we don't modify the original
    environment_dict = dict(os.environ)

    # Update the environment variables
    environment_dict["KOPS_STATE_STORE"] = KOPS_STATE_STORE
    environment_dict["PROJECT"] = PROJECT

    create_bucket_command = ["gsutil", "mb", KOPS_STATE_STORE]
    run_command(create_bucket_command, environment_dict)

    create_command = ["kops", "create", "-f", yaml_file]
    run_command(create_command, environment_dict)

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
    run_command(create_secret_command, environment_dict)

    update_command = ["kops", "update", "cluster", "--name", cluster_name, "--yes", "--admin"]
    run_command(update_command, environment_dict)

    validate_command = ["kops", "validate", "cluster", "--wait", "10m"]
    run_command(validate_command, environment_dict)

    print("########### Cluster started ###########")


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


def get_node_info() -> list[list[str]]:
    return get_info("nodes")


def get_pods_info() -> list[list[str]]:
    return get_info("pods")


def get_jobs_info() -> list[list[str]]:
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
