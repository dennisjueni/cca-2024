import click
from loguru import logger
from scripts.utils import delete_cluster, run_command


@click.command()
@click.option("--cluster_name", "-c", help="Name of the cluster to delete", type=str)
def delete_cluster_cli(cluster_name: str) -> None:

    delete_cluster(cluster_name)
    print("########### Cluster deleted ###########")


@click.command()
def delete_pods() -> None:
    logger.info("Deleting all jobs.")
    run_command(["kubectl", "delete", "jobs", "--all"])
    logger.info("Deleting all pods.")
    run_command(["kubectl", "delete", "pods", "--all"])
    logger.info("Deleting all services.")
    run_command(["kubectl", "delete", "services", "--all"])
    logger.success("########### Pods, Jobs & Services deleted ###########")

