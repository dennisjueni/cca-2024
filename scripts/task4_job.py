from task4_config import DOCKERIMAGES, JobEnum
import docker.models.containers


class ControllerJob:
    def __init__(self, job: JobEnum):
        self.job = job
        self.image = DOCKERIMAGES[job]
        self.container: docker.models.containers.Container = None

    def _set_container(self, container: docker.models.containers.Container):
        self.container = container

    def _run_command(self, nr_threads: int) -> str:
        benchmark_suite = "parsec" if self.job != JobEnum.RADIX else "splash2x"
        benchmark_name = self.job.value
        return f"./run -a run -S {benchmark_suite} -p {benchmark_name} -i native -n {nr_threads}"

    def __repr__(self):
        return f"<ControllerJob: {self.job}>"
