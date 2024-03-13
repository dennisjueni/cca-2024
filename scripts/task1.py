from time import sleep
import subprocess
import click
import time
import os

from utils import start_cluster, run_command, pods_ready, get_node_info, get_pods_info, copy_file_to_node


@click.command()
@click.option("--start", "-s", help="Flag indicating if the cluster should be started", is_flag=True, default=False, type=bool)
def task1(start: bool):

    DEBUG = True

    # setup(start, debug=DEBUG)

    # start_memcached(debug=DEBUG)

    type = "no_interference"
    print(f"Starting pod of type {type}")
    print("Pod ready")

    run_tests(type, 5, debug=DEBUG)

    for file in os.listdir("./interference"):
        if file.endswith(".yaml"):
            type = file.split(".")[0]
    
    


def run_tests(type: str, num_iterations: int, debug: bool = False) -> None:
    print("########### Running tests ###########")
    node_info = get_node_info()
    pod_info = get_pods_info()

    for line in node_info:
        if line[0].startswith("client-agent"):
            client_agent_ip = line[5]
        elif line[0].startswith("client-measure"):
            client_measure_name = line[0]
    
    for line in pod_info:
        if line[0].startswith("some-memcached"):
            memcached_ip = line[5]

    for i in range(num_iterations):
        filename = f"./results/agent_{type}_{i}"
        with open(filename+'.txt', "w") as f:
            res = subprocess.run(
                [
                    "gcloud",
                    "compute",
                    "ssh",
                    "--zone",
                    "europe-west3-a",
                    "--ssh-key-file",
                    os.path.expanduser("~/.ssh/cloud-computing"),
                    "ubuntu@" + client_measure_name,
                    "--command",
                    f"./memcache-perf/mcperf -s {memcached_ip} -a {client_agent_ip} --noload -T 16 -C 4 -D 4 -Q 1000 -c 4 -t 5 -w 2 --scan 5000:55000:5000",
                ],
                stdout=f,
            )


def setup(start: bool, debug: bool = False) -> None:
    """Sets up the environment for task 1. This includes starting the cluster, launching memcached and installing memcached on the nodes client-agent and client-measure."""

    if start:
        start_cluster("part1.yaml", debug=debug)
    else:
        print("Skipped starting the cluster")
    
    launch_memcached(debug=debug)
    install_memcached(debug=debug)


def launch_memcached(debug: bool = False) -> None:
    print("########### Starting Memcached ###########")

    # If Memcached is already running, we don't need to do anything
    if pods_ready(debug=debug):
        print("########### Memcached already running ###########")
        return

    create_memcached_command = ["kubectl", "create", "-f", "memcache-t1-cpuset.yaml"]
    run_command(create_memcached_command, should_print=debug)

    expose_memcached_command = ["kubectl", "expose", "pod", "some-memcached", "--name", "some-memcached-11211", "--type", "LoadBalancer", "--port", "11211", "--protocol", "TCP"]
    run_command(expose_memcached_command, should_print=debug)
        

    while not pods_ready(debug=debug):
        time.sleep(10)

    print("########### Memcached started ###########")


def install_memcached(debug: bool = False) -> None:
    print("########### Installing Memcached ###########")
    node_info = get_node_info(debug=debug)

    source_path = "./scripts/install_memcached.sh"
    destination_path = "~/install_memcached.sh"

    for line in node_info:
        if line[0].startswith("client-agent") or line[0].startswith("client-measure"):

            # First we check if we have already copied the file to the node, if so we do not do it again
            check_command = ["gcloud", "compute", "ssh", f"ubuntu@{line[0]}", "--zone", "europe-west3-a", "--ssh-key-file", os.path.expanduser("~/.ssh/cloud-computing"), "--command", f"test -f {destination_path} && echo 'already installed' || echo '-'"]
            res = subprocess.run(check_command, env=dict(os.environ), capture_output=True)

            if "already installed" in res.stdout.decode("utf-8"):
                print(f"Memcached already installed on {line[0]}")
                continue

            copy_file_to_node(line[0], source_path=source_path, destination_path=destination_path, debug=debug)

            # Installing the file 
            print(f"Installing memcached on {line[0]}")
            install_command = ["gcloud", "compute", "ssh", f"ubuntu@{line[0]}", "--zone", "europe-west3-a", "--ssh-key-file", os.path.expanduser("~/.ssh/cloud-computing"), "--command", f"chmod +x {destination_path} && {destination_path}"]
            
            run_command(install_command, should_print=debug)
    print("########### Finished Installing Memcached ###########")


def start_memcached(debug: bool = False) -> None:
    print("########### Starting Memcached ###########")
    node_info = get_node_info()
    pod_info = get_pods_info()

    for line in node_info:
        if line[0].startswith("client-agent"):
            client_agent_name = line[0]
        elif line[0].startswith("client-measure"):
            client_measure_name = line[0]
    
    for line in pod_info:
        if line[0].startswith("some-memcached"):
            memcached_ip = line[5]
    
    mcperf_agent_command = ["gcloud", "compute", "ssh", "--zone", "europe-west3-a", "--ssh-key-file", os.path.expanduser("~/.ssh/cloud-computing"), "ubuntu@" + client_agent_name, "--command", "./memcache-perf/mcperf -T 16 -A"]
    subprocess.Popen(mcperf_agent_command)

    print("Agent started")

    sleep(5)

    mcperf_measure_command = [ "gcloud", "compute", "ssh", "--zone", "europe-west3-a", "--ssh-key-file", os.path.expanduser("~/.ssh/cloud-computing"), "ubuntu@" + client_measure_name, "--command", f"./memcache-perf/mcperf -s {memcached_ip} --loadonly"]
    res = subprocess.run(mcperf_measure_command)

    print("########### Starting Memcached ###########")

if __name__ == "__main__":
    task1()