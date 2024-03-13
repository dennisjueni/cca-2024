import click
import time

from utils import start_cluster, run_command, pods_ready


@click.command()
@click.option("--start", "-s", help="Flag indicating if the cluster should be started", is_flag=True, default=False, type=bool)
def task1(start: bool):
    if start:
        start_cluster("part1.yaml", debug=True)
    else:
        print("Skipped starting the cluster")
    
    # run_memcached()



# WIP!
def run_memcached():
    create_memcached_command = ["kubectl", "create", "-f", "memcache-t1-cpuset.yaml"]
    run_command(create_memcached_command, should_print=True)

    expose_memcached_command = ["kubectl", "expose", "pod", "some-memcached", "--name", "some-memcached-11211", "--type", "LoadBalancer", "--port", "11211", "--protocol", "TCP"]
    run_command(expose_memcached_command, should_print=True)

    while not pods_ready():
        # TODO: Take this print out if it's working as expected (added for now to check if everything is working as intended)
        print("Waiting for pods to be ready")
        time.sleep(10)

    print("Pods are ready")



if __name__ == "__main__":
    task1()