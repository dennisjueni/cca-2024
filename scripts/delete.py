import click
from scripts.utils import delete_cluster


@click.command()
@click.option("--debug", "-d", help="Debug Flag for deleting the cluster.", is_flag=True, default=False, type=bool)
def delete_cluster_cli(debug: bool) -> None:
    delete_cluster(debug=debug)
    print("########### Cluster deleted ###########")

if __name__ == "__main__":
    delete_cluster_cli()
