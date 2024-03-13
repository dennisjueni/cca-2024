import click
from scripts.utils import delete_cluster


if __name__ == "__main__":
    delete_cluster(debug=True)
    print("########### Cluster deleted ###########")


@click.command()
@click.option("--debug", "-d", help="Debug Flag for deleting the cluster.", is_flag=True, default=False, type=bool)
def delete_cluster_cli(debug: bool) -> None:
    delete_cluster(debug=debug)
