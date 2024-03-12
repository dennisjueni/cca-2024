import os
import subprocess


KOPS_STATE_STORE = "gs://cca-eth-2024-group-076-djueni/"
PROJECT = "gcloud config get-value project"


def start_cluster(yaml_file: str) -> None:
    print("########### Starting cluster ###########")

    # We create a copy of the current environment variables to make sure we don't modify the original
    environment_dict = dict(os.environ)
    
    # Update teh environment variables
    environment_dict["KOPS_STATE_STORE"] = KOPS_STATE_STORE
    environment_dict["PROJECT"] = PROJECT

    command = ["kops", "create", "-f", yaml_file]
    res = subprocess.run(command, env=environment_dict, capture_output=True)

    if res.stderr:
        print("\033[91m!!! ERROR OCCURED !!!\033[0m") # Print in red
        print(res.stderr.decode("utf-8"))
    else:
        print(res.stdout.decode("utf-8"))
