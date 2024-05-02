import yaml
import tempfile
import os

from loguru import logger

from scripts.utils import pods_completed, run_command


PARSEC_PATH = os.path.join(".", "parsec-benchmarks", "part3")


class Job:
    def __init__(
        self,
        job_name: str,
        benchmark: str,
        node_selector: str,
        cores: str,
        nr_threads: int,
        benchmark_suite="parsec",
        depends_on=[],
    ):
        self.job_name = job_name
        self.benchmark = benchmark
        self.node_selector = node_selector
        self.cores = cores
        self.nr_threads = nr_threads
        self.benchmark_suite = benchmark_suite
        self.depends_on = depends_on
        self.file = self._create_file()
        self.is_finished_prop = False
        self.started = False

    def _create_file(self):
        return modified_yaml_file(
            os.path.join(PARSEC_PATH, f"parsec-{self.job_name}.yaml"),
            selector=node_selector(self.node_selector),
            container_args=container_args(
                self.cores, self.benchmark, self.nr_threads, benchmark_suite=self.benchmark_suite
            ),
        )

    @property
    def is_finished(self):
        self.is_finished_prop = self.is_finished_prop or pods_completed(self.job_name)
        return self.is_finished_prop

    def start(self):
        if self.started:
            return
        for job in self.depends_on:
            if not job.is_finished:
                logger.info(f"{self.job_name} is waiting for {job.job_name} to finish. Try again later.")
                return
        run_command(f"kubectl create -f {self.file.name}".split())
        self.started = True
        logger.info(f"Started job {self.job_name}")
        self.file.close()

    def apply(self):
        # TODO: kubectl currently not working as hoped, find out how kubectl apply works or remove it
        run_command(f"kubectl apply -f {self.file.name}".split())
        logger.info(f"applied job {self.job_name}")


def __taskset_command(cores: str, benchmark_name: str, nr_threads: int, benchmark_suite="parsec") -> list:
    # args: ["-c", "taskset -c 4,5,6 ./run -a run -S parsec -p canneal -i native -n 3"]
    return [
        "-c",
        f"taskset -c {cores} ./run -a run -S {benchmark_suite} -p {benchmark_name} -i native -n {nr_threads}",
    ]


def container_args(cores: str, benchmark: str, nr_threads: int, benchmark_suite="parsec") -> tuple:
    return ["spec", "template", "spec", "containers", 0, "args"], __taskset_command(
        cores, benchmark, nr_threads, benchmark_suite=benchmark_suite
    )


def node_selector(selector_value: str) -> tuple:
    return ["spec", "template", "spec", "nodeSelector", "cca-project-nodetype"], selector_value


def modified_yaml_file(file_path, **kwargs):
    """
    Usage example:
        modify_yaml_file("file.yaml", lambda file: run_command(f"cat {file.name}"), value1=([key1, subkey2], "modified_value"))
    """
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

    # Traverse the attribute path and update the value
    for attribute_path, new_value in kwargs.values():
        current_node = data
        for key in attribute_path[:-1]:
            current_node = current_node[key]  # can be a list or a dict
        if current_node:
            current_node[attribute_path[-1]] = new_value
        else:
            raise ValueError(f"Attribute path '{attribute_path}' not found in YAML")

    # Write modified data to a temporary file
    temp_file = tempfile.NamedTemporaryFile(mode="w")
    yaml.dump(data, temp_file, default_flow_style=False)
    return temp_file
