"""
This python script should run alongside `memcached` on 
"""

import time
from typing import Union
import docker
import docker.models
import docker.models.containers
from loguru import logger
from task4_scheduler_logger import SchedulerLogger
from task4_job import ControllerJob
from task4_config import JobEnum
from docker.client import DockerClient
import psutil
import subprocess


def memcached_pid() -> str:
    try:
        # Run pidof command and capture output
        output = subprocess.check_output(["pidof", "memcached"]).decode("utf-8").strip()
        # Extract the first PID (assuming only one found)
        pid = output.split()[0]
        return pid
    except subprocess.CalledProcessError:
        print(f"Process 'memcached' not found")
        raise ValueError("Could not resolve pid of memcached. Is it running?")


class Controller:
    def __init__(self):
        self.client: DockerClient = docker.from_env()
        self.jobs: list[ControllerJob] = []
        self.memcached_pid = memcached_pid()
        self.num_memcached_cores = -1 # to not block the memcached set cores
        self.logger = SchedulerLogger()

    def set_memcached_cores(self, cores: list[int]):
        if len(cores) == self.num_memcached_cores:
            return
        self.num_memcached_cores = len(cores)
        taskset_command = f"sudo taskset -a -c {','.join(list(map(str, cores)))} -p {self.memcached_pid}"
        subprocess.run(taskset_command.split())
        self.logger.update_cores(JobEnum.MEMCACHED, cores=cores)

    def start_controlling(self):
        self.logger.job_start(JobEnum.MEMCACHED, initial_cores=[0], initial_threads=2)
        self.set_memcached_cores([0])
        self.create_jobs()
        self.schedule_loop()

    def job_create(self, job_enum: JobEnum) -> None:
        controller_job = ControllerJob(job_enum, client=self.client, logger=self.logger)

        logger.info(f"Creating {str(job_enum)}-container with image: {controller_job.image}")

        controller_job.create_container(cores=[1, 2, 3])

        self.jobs.append(controller_job)
        logger.info(f"Created {str(controller_job)} container with id {controller_job.container.short_id}")

    def create_jobs(self):
        for job in JobEnum:
            if job == JobEnum.MEMCACHED or job == JobEnum.SCHEDULER:
                continue
            self.job_create(job)

    def extract_job(self, job: Union[JobEnum, ControllerJob]) -> ControllerJob:
        assert isinstance(job, JobEnum) or isinstance(job, ControllerJob), f"Invalid job type: {type(job)}"

        if isinstance(job, JobEnum):
            for controller_job in self.jobs:
                if controller_job.job == job:
                    job = controller_job
                    return controller_job
            raise ValueError(f"Job {job} not found in current jobs: {self.jobs}")

        return job

    def monitor_container_cpu(self):
        for job in self.jobs:
            stats = job.container.stats(stream=False)
            logger.info(f"Stats for {str(job)} container: {stats}")

            cpu_percent = stats["cpu_stats"]["cpu_usage"]["total_usage"] / stats["cpu_stats"]["system_cpu_usage"] * 100
            logger.info(f"{str(job)} container CPU usage: {cpu_percent:.2f}%")

    def monitor_system_stats(self) -> list[float]:
        cpu_percent = psutil.cpu_percent(percpu=True)
        return cpu_percent

    def is_memcached_overloaded(self, cpu_threshold) -> bool:
        cpu_percent = self.monitor_system_stats()

        if self.num_memcached_cores == 1:
            return cpu_percent[0] > cpu_threshold

        return cpu_percent[0] + cpu_percent[1] > cpu_threshold

    def is_memcached_underloaded(self, cpu_threshold) -> bool:
        return not self.is_memcached_overloaded(cpu_threshold)

    def schedule_loop(self):

        OVERLOADED_THRESHOLD = 75 # This is only 1 core
        UNDERLOADED_THRESHOLD = 90  # This is for two cores

        current_job = self.jobs.pop(0)
        current_job.start_container()

        while True:
            curr_job_finished = current_job.has_finished()

            if curr_job_finished:
                if len(self.jobs) == 0:
                    # This means we have finished all jobs and we can thus break the loop and let memcached run alone
                    break

                # This means we can start the next job in the list and run it optimistically on 3 cores
                current_job = self.jobs.pop(0)
                current_job.start_container()

                if self.num_memcached_cores != 1:
                    current_job.update_cores([2, 3])
            else:
                if self.num_memcached_cores == 1 and self.is_memcached_overloaded(OVERLOADED_THRESHOLD):
                    self.set_memcached_cores([0, 1])
                    current_job.update_cores([2, 3])

                elif self.num_memcached_cores == 2 and self.is_memcached_underloaded(UNDERLOADED_THRESHOLD):
                    self.set_memcached_cores([0])
                    current_job.update_cores([1, 2, 3])

            time.sleep(0.25)

        time.sleep(70)
        self.logger.job_end(JobEnum.MEMCACHED)

if __name__ == "__main__":
    controller = Controller()
    controller.start_controlling()
