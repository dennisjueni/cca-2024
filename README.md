# Cloud Computing Architecture Project

In this project, we explored how to schedule latency-sensitive and batch applications in a cloud cluster using Kubernetes on GCloud.

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

## Part 3

- Kubernetes Cluster consisting of (`part3.yml`) :
  - 1 Master VM
  - 3 (2 agents + 1 measure) `mcperf` VMs
  - 3 heterogeneous `nemcached` VMs
- Goal : Scheduling (for best possible speed) of seven batch workloads (`blackscholes`, `canneal`, ...) under the constraint that `memcached` responds to 95% of requests within 1 millisecond, even with 30,000 requests per second (QPS). I.e.
  $$s^* = \underset{s \in \text{ Schedules}}{\arg\min} \sum_{j\in\text{ Jobs}} t_j(\text{s}) \quad \text{ s.t.}$$
  1. `memcached` responds to $95\%$ of requests within $1$ms given $\text{QPS} \leq 30\text{k}\frac{\text{requests}}{s}$
  2. No errors (e.g. out of memory)

## Part 4

- Cluster of 4 nodes:

|         Node Name         |  Role  |  Machine Type  |                 Labels                 |
| :-----------------------: | :----: | :------------: | :------------------------------------: |
|   master-europe-west3-a   | Master | e2-standard-2  |                   -                    |
|      memcache-server      |  Node  | n2d-highmem-4  |   cca-project-nodetype: "memcached"    |
| client-measure (`mcperf`) |  Node  | e2-standard-2  | cca-project-nodetype: "client-measure" |
|  client-agent (`mcperf`)  |  Node  | e2-standard-16 |  cca-project-nodetype: "client-agent"  |

## FAQ
- **How to select the correct Python interpreter path to make MissingImportWarnings disappear?**

    First, find the place where poetry created the venv. (Should be in the project root if `poetry config virtualenvs.in-project true`)
    You can do that using this command when inside of the poetry shell: `bash poetry env info -p`
    Then simply select this as Python interpreter path in VSCode


# TODO
- Coschedule RADIX with Memcached (bc almost no interference)
