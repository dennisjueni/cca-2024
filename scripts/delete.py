import click
from scripts.utils import delete_cluster


@click.command()
@click.option("--cluster_name", "-c", help="Name of the cluster to delete", type=str)
@click.option("--debug", "-d", help="Debug Flag for deleting the cluster.", is_flag=True, default=False, type=bool)
def delete_cluster_cli(cluster_name: str, debug: bool) -> None:

    delete_cluster(cluster_name, debug=debug)
    print("########### Cluster deleted ###########")


if __name__ == "__main__":
    delete_cluster_cli()
