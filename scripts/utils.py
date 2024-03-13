import os
import subprocess


KOPS_STATE_STORE = "gs://cca-eth-2024-group-076-djueni/"
PROJECT = "gcloud config get-value project"

def run_command(command: list[str], env: dict[str, str] = dict(os.environ), should_print=True) -> None:
    res = subprocess.run(command, env=env, capture_output=True)
    if res.returncode != 0:
        print("\033[91m!!! ERROR OCCURED !!!\033[0m") # Print in red
        print(res.stderr.decode("utf-8"))
    elif should_print:
        print(res.stdout.decode("utf-8"))


def start_cluster(yaml_file: str, debug=False) -> None:
    print("########### Starting cluster ###########")

    # We create a copy of the current environment variables to make sure we don't modify the original
    environment_dict = dict(os.environ)
    
    # Update teh environment variables
    environment_dict["KOPS_STATE_STORE"] = KOPS_STATE_STORE
    environment_dict["PROJECT"] = PROJECT

    create_command = ["kops", "create", "-f", yaml_file]
    run_command(create_command, environment_dict, should_print=debug)

    create_secret_command = ["kops", "create", "secret", "--name", "part1.k8s.local", "sshpublickey", "admin", "-i", os.path.expanduser("~/.ssh/cloud-computing.pub")]
    run_command(create_secret_command, environment_dict, should_print=debug)

    update_command = ["kops", "update", "cluster", "--name", "part1.k8s.local", "--yes", "--admin"]
    run_command(update_command, environment_dict, should_print=debug)

    validate_command = ["kops", "validate", "cluster", "--wait", "10m"]
    run_command(validate_command, environment_dict, should_print=debug)

    print("########### Cluster started ###########")


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