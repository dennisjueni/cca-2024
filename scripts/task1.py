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
    
    start_memcached(debug=True)

    # TODO: Install memcached on the respective machines
    #install_memcached(debug=True)



def start_memcached(debug: bool = False) -> None:
    print("########### Starting Memcached ###########")

    create_memcached_command = ["kubectl", "create", "-f", "memcache-t1-cpuset.yaml"]
    run_command(create_memcached_command, should_print=debug)

    expose_memcached_command = ["kubectl", "expose", "pod", "some-memcached", "--name", "some-memcached-11211", "--type", "LoadBalancer", "--port", "11211", "--protocol", "TCP"]
    run_command(expose_memcached_command, should_print=debug)

    while not pods_ready(debug=debug):
        time.sleep(10)

    print("########### Memcached started ###########")



def install_memcached(debug: bool = False) -> None:
    pass



if __name__ == "__main__":
    task1()