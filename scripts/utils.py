import os
import subprocess


KOPS_STATE_STORE = "gs://cca-eth-2024-group-076-djueni/"
PROJECT = "gcloud config get-value project"

def run_and_print_command(command: list[str], env: dict[str, str]) -> None:
    res = subprocess.run(command, env=env, capture_output=True)
    if res.stderr:
        print("\033[91m!!! ERROR OCCURED !!!\033[0m") # Print in red
        print(res.stderr.decode("utf-8"))
    else:
        print(res.stdout.decode("utf-8"))


def start_cluster(yaml_file: str) -> None:
    print("########### Starting cluster ###########")

    # We create a copy of the current environment variables to make sure we don't modify the original
    environment_dict = dict(os.environ)
    
    # Update teh environment variables
    environment_dict["KOPS_STATE_STORE"] = KOPS_STATE_STORE
    environment_dict["PROJECT"] = PROJECT

    create_command = ["kops", "create", "-f", yaml_file]
    run_and_print_command(create_command, environment_dict)

    create_secret_command = ["kops", "create", "secret", "--name", "part1.k8s.local", "sshpublickey", "admin", "-i", "~/.ssh/cloud-computing.pub"]
    run_and_print_command(create_secret_command, environment_dict)

    update_command = ["kops", "update", "cluster", "--name", "part1.k8s.local", "--yes", "--admin"]
    run_and_print_command(update_command, environment_dict)

    validate_command = ["kops", "validate", "cluster", "--wait", "10m"]
    run_and_print_command(validate_command, environment_dict)

    print("########### Cluster started ###########")