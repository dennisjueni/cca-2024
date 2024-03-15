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


def run_command(command: list[str], env: dict[str, str] = dict(os.environ), should_print=True) -> None:
    res = subprocess.run(command, env=env, capture_output=True)
    if res.returncode != 0:
        print("\033[91m!!! ERROR OCCURED !!!\033[0m")  # Print in red
        print(res.stderr.decode("utf-8"))
    elif should_print:
        print(res.stdout.decode("utf-8"))


def start_cluster(yaml_file: str, debug=False) -> None:
    print("########### Starting cluster ###########")

    # We create a copy of the current environment variables to make sure we don't modify the original
    environment_dict = dict(os.environ)

    # Update the environment variables
    environment_dict["KOPS_STATE_STORE"] = KOPS_STATE_STORE
    environment_dict["PROJECT"] = PROJECT

    create_bucket_command = ["gsutil", "mb", KOPS_STATE_STORE]
    run_command(create_bucket_command, environment_dict, should_print=debug)

    create_command = ["kops", "create", "-f", yaml_file]
    run_command(create_command, environment_dict, should_print=debug)

    create_secret_command = [
        "kops",
        "create",
        "secret",
        "--name",
        "part1.k8s.local",
        "sshpublickey",
        "admin",
        "-i",
        os.path.expanduser("~/.ssh/cloud-computing.pub"),
    ]
    run_command(create_secret_command, environment_dict, should_print=debug)

    update_command = ["kops", "update", "cluster", "--name", "part1.k8s.local", "--yes", "--admin"]
    run_command(update_command, environment_dict, should_print=debug)

    validate_command = ["kops", "validate", "cluster", "--wait", "10m"]
    run_command(validate_command, environment_dict, should_print=debug)

    print("########### Cluster started ###########")


def delete_cluster(debug=False) -> None:
    # We create a copy of the current environment variables to make sure we don't modify the original
    environment_dict = dict(os.environ)

    # Update the environment variables
    environment_dict["KOPS_STATE_STORE"] = KOPS_STATE_STORE
    environment_dict["PROJECT"] = PROJECT

    delete_comand = ["kops", "delete", "cluster", "part1.k8s.local", "--yes"]
    run_command(delete_comand, environment_dict, should_print=debug)

    delete_bucket_command = ["gsutil", "rm", "-r", KOPS_STATE_STORE]
    run_command(delete_bucket_command, environment_dict, should_print=debug)

    print("########### Cluster deleted ###########")


def get_info(resource_type: str, debug: bool = False) -> list[list[str]]:
    get_command = ["kubectl", "get", resource_type, "-o", "wide"]
    res = subprocess.run(get_command, env=dict(os.environ), capture_output=True)

    if debug:
        print(res.stdout.decode("utf-8"))

    # Split the output into lines and remove the first line (header)
    lines = res.stdout.decode("utf-8").split("\n")[1:]

    # Split each line into a list of strings and remove empty lines and empty strings
    info = [line.split(" ") for line in lines if line != ""]
    info = [[s for s in line if s != ""] for line in info]
    return info


def get_node_info(debug: bool = False) -> list[list[str]]:
    return get_info("nodes", debug=debug)


def get_pods_info(debug: bool = False) -> list[list[str]]:
    return get_info("pods", debug=debug)


def pods_ready(debug: bool = False) -> bool:
    info = get_pods_info(debug=debug)

    if len(info) == 0:
        return False

    for pod in info:
        if pod[1] != "1/1" or pod[2] != "Running":
            return False
    return True


def copy_file_to_node(node: str, source_path: str, destination_path: str, debug: bool = False) -> None:

    if debug:
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
    run_command(copy_command, dict(os.environ), should_print=debug)


def check_output(res: subprocess.CompletedProcess) -> None:
    if res.returncode != 0:
        print(res.stderr.decode("utf-8"))
        sys.exit(1)
