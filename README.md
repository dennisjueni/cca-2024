# Cloud Computing Architecture Project

## Before running the scripts

1. You probably need to login to gcloud in your console, maybe with this command?
    ```
    gcloud auth application-default login
    ```
2. You need to create an SSH key to be able to access the VMs. Use the exact command below (the filename must match exactly)
    ```
    $ cd ~/.ssh
    $ ssh-keygen -t rsa -b 4096 -f cloud-computing
    ```

3. You need to install the necessary dependencies:
    ```bash
    pip install -r requirements.txt
    # or
    pip install poetry
    poetry install
    poetry shell # activate the virtual environment
    ```

## Running task 1 script

To run the script for task1 run the following. f the cluster is already started, remove the --start flag:
```bash
$ python3 scripts/task1.py --start
# alternatively if poetry project
run_task1 --start
```