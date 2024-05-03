from loguru import logger
import psutil
from task4_config import DOCKERIMAGES, JobEnum
import docker.models.containers
import random


class ControllerJob:
    def __init__(self, job: JobEnum):
        self.job = job
        self.image = DOCKERIMAGES[job]
        self.container: docker.models.containers.Container = None
        self.is_paused = False

    def _set_container(self, container: docker.models.containers.Container):
        self.container = container

    def _run_command(self, nr_threads: int) -> str:
        benchmark_suite = "parsec" if self.job != JobEnum.RADIX else "splash2x"
        benchmark_name = self.job.value
        return f"./run -a run -S {benchmark_suite} -p {benchmark_name} -i native -n {nr_threads}"

    def has_finished(self) -> bool:
        return self.container.status == "exited"

    def _get_cores(self) -> list[str]:
        logger.debug(f"Getting cores for {str(self)} container: {self.container.attrs['HostConfig']['CpusetCpus']}")
        return self.container.attrs["HostConfig"]["CpusetCpus"].split(",")

    def _available_cores(self) -> list[str]:
        return [str(i) for i in range(0, psutil.cpu_count())]

    def add_core(self) -> None:
        logger.info(f"Adding cores to {str(self)} container")
        available_cores = self._available_cores()
        cores = self._get_cores()
        for core in cores:
            available_cores.remove(core)
        random_cores = random.sample(available_cores, 1)
        cores.append(random_cores)
        self.update_cores(cores)

    def end(self) -> None:
        logger.info(f"Ending {str(self)} container with id {self.container.short_id}")
        self.container.stop()

    def update_cores(self, cores: list[str]) -> None:
        logger.info(f"Updating {str(self)} container with cores {cores}")
        self.cpu_cores = cores
        self.container.update(cpuset_cpus=",".join(cores))

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
