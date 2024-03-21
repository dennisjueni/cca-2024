import click
from scripts.utils import delete_cluster


@click.command()
@click.option("--cluster_name", "-c", help="Name of the cluster to delete", type=str)
def delete_cluster_cli(cluster_name: str) -> None:

    delete_cluster(cluster_name)
    print("########### Cluster deleted ###########")


if __name__ == "__main__":
    delete_cluster_cli()
