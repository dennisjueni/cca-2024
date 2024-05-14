import click
from loguru import logger

from scripts.utils import delete_cluster, run_command


@click.command()
def delete_cluster_cli() -> None:
    for i in range(1, 5):
        cluster_name = f"part{i}.k8s.local"
        try:
            delete_cluster(cluster_name)
        except Exception as e:
            logger.error(f"Error deleting cluster {cluster_name}: {e}")
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
