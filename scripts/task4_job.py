import docker.errors
from loguru import logger
from task4_scheduler_logger import SchedulerLogger
from task4_config import CPU_CORES, DOCKERIMAGES, NR_THREADS, JobEnum
import docker.models.containers
from docker.client import DockerClient

class ControllerJob:

    def __init__(self, job: JobEnum, client: DockerClient, logger: SchedulerLogger):
        self.job = job
        self.client = client
        self.logger = logger

        self.image = DOCKERIMAGES[job]
        self.nr_threads = NR_THREADS[job]
        self.cpu_cores = CPU_CORES[job]
        self.is_paused = False
        self.thresholds = [None, None]

        self.container: docker.models.containers.Container

    @property
    def run_command(self) -> str:
        benchmark_suite = "parsec" if self.job != JobEnum.RADIX else "splash2x"
        benchmark_name = self.job.value
        return f"./run -a run -S {benchmark_suite} -p {benchmark_name} -i native -n {self.nr_threads}"

    def create_container(self) -> docker.models.containers.Container:
        self.client.images.pull(self.image)

        self.container = self.client.containers.create(
            self.image,
            name=self.job.value,
            cpuset_cpus=",".join(list(map(str, self.cpu_cores))),
            command=self.run_command,
            detach=True,
        )  # type: ignore

        # If the container is created, it does not start yet so we set the state to paused
        self.is_paused = True

        return self.container  # type: ignore

    def start_container(self) -> bool:
        self.container.start()
        self.logger.job_start(self.job, self.cpu_cores, self.nr_threads)
        self.is_paused = False
        return True

    def is_finished(self) -> bool:
        self.container.reload()
        is_finished = self.container.status.lower().startswith("exited")

        if is_finished:
            self.logger.job_end(self.job)

        return is_finished

    def is_running(self) -> bool:
        self.container.reload()
        is_running = self.container.status.lower().startswith("running")

        return is_running

    def get_cores(self) -> list[int]:
        return self.cpu_cores

    def update_cores(self, cores: list[int]) -> None:
        if str(cores) == str(self.cpu_cores) or not self.is_running():
            return

        logger.info(f"Updating {str(self)} container with cores {cores}")

        try:
            self.cpu_cores = cores
            self.container.update(cpuset_cpus=",".join(list(map(str, cores))))
            self.logger.update_cores(self.job, cores)
        except docker.errors.APIError as e:
            if e.explanation and "cannot update a stopped container" in e.explanation:
                logger.info(f"This most likely means that the container was not running anymore so we just return")
                return
            raise e

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
