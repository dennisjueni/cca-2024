from typing import List
from loguru import logger
import psutil
from task4_scheduler_logger import SchedulerLogger
from task4_config import DOCKERIMAGES, NR_THREADS, JobEnum
import docker.models.containers
import random
from docker.client import DockerClient

class ControllerJob:

    def __init__(self, job: JobEnum, client: DockerClient, logger: SchedulerLogger):
        self.job = job
        self.image = DOCKERIMAGES[job]
        self.is_paused = False
        self.client = client
        self.container: docker.models.containers.Container
        self.nr_threads = NR_THREADS[job]
        if self.nr_threads == 2:
            self.cpu_cores = [2, 3]
        else:
            self.cpu_cores = [1, 2, 3]
        self.logger = logger

    @property
    def _run_command(self) -> str:
        benchmark_suite = "parsec" if self.job != JobEnum.RADIX else "splash2x"
        benchmark_name = self.job.value
        return f"./run -a run -S {benchmark_suite} -p {benchmark_name} -i native -n {self.nr_threads}"

    def create_container(self, cores: list[int], **kwargs) -> docker.models.containers.Container:
        kwargs["detach"] = kwargs.get("detach", True)

        self.client.images.pull(self.image)

        self.container = self.client.containers.create(
            self.image,
            name=self.job.value,
            cpuset_cpus=",".join(list(map(str, cores))),
            command=self._run_command,
            **kwargs,
        )  # type: ignore

        # If the container is created, it does not start yet so we set the state to paused
        self.is_paused = True

        return self.container  # type: ignore

    def start_container(self) -> bool:
        self.container.start()
        self.logger.job_start(self.job, self.cpu_cores, self.nr_threads)
        self.is_paused = False
        return True

    def has_finished(self) -> bool:
        self.container.reload()
        has_finished = self.container.status.lower().startswith("exited")

        if has_finished:
            self.logger.job_end(self.job)

        return has_finished

    def get_cores(self) -> list[int]:
        return self.cpu_cores

    def _available_cores(self) -> list[int]:
        return [i for i in range(0, psutil.cpu_count())]

    def add_core(self) -> None:
        logger.info(f"Adding cores to {str(self)} container")
        available_cores: list[int] = self._available_cores()
        cores: list[int] = self.get_cores()
        for core in cores:
            available_cores.remove(core)

        if len(available_cores) == 0:
            logger.warning(f"No available cores to add to {str(self)} container")
            return

        # get a random core out of the list available_cores
        random_core = random.choice(available_cores)
        cores.append(random_core)
        self.update_cores(cores)

    def end(self) -> None:
        logger.info(f"Ending {str(self)} container with id {self.container.short_id}")
        self.container.stop()

    def remove(self) -> None:
        logger.info(f"Removing {str(self)} container with id {self.container.short_id}")
        self.container.remove()

    def update_cores(self, cores: list[int]) -> None:
        # invariant: The list of cores is always available!
        logger.info(f"Updating {str(self)} container with cores {cores}")
        self.cpu_cores = cores
        self.container.update(cpuset_cpus=",".join(list(map(str, cores))))
        self.logger.update_cores(self.job, cores)

    def pause(self) -> None:
        logger.info(f"Pausing {str(self)} container with id {self.container.short_id}")
        self.is_paused = True
        self.container.pause()

    def unpause(self) -> None:
        logger.info(f"Unpausing {str(self)} container with id {self.container.short_id}")
        self.container.unpause()
        self.is_paused = False

    def __repr__(self):
        return f"<ControllerJob: {self.job}>"

    def info(self):
        return f"Info {str(self)}:\n{str(self.container.attrs)}"
