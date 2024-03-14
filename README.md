# Cloud Computing Architecture Project

## Before running the scripts

1. You probably need to login to gcloud in your console, maybe with this command?
    ```bash
    gcloud auth application-default login
    ```
2. You need to create an SSH key to be able to access the VMs. Use the exact command below (the filename must match exactly)
    ```bash
    cd ~/.ssh
    ssh-keygen -t rsa -b 4096 -f cloud-computing
    ```

3. You need to install the necessary dependencies (insall poetry first):
    ```bash
    poetry install
    # activate the virtual environment
    poetry shell

    # To exit the virtual environment
    exit
    ```

## Running task 1 script

To run the script for task1 run the following. If the cluster is already started, remove the --start flag:
```bash
# If in poetry shell
run_task1 --start

# If not in poetry shell
poetry run run_task1 --start

```

## Deleting the cluster

```bash
# If in poetry shell
delete_cluster

# If not in poetry shell
poetry run delete_cluster
```

## FAQ
- **How to select the correct Python interpreter path to make MissingImportWarnings disappear?**

    First, find the place where poetry created the venv.
    You can do that using this command when inside of the poetry shell: `bash poetry env info -p`
    Then simply select this as Python interpreter path in VSCode