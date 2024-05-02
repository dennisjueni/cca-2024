"""
This python script should run alongside `memcached` on 
"""

import time
from typing import Union
import docker
from datetime import datetime

import docker.models
import docker.models.containers
from loguru import logger
from scripts.task4_job import ControllerJob
from task4_config import *
from docker.client import DockerClient
import psutil


class Controller:
    def __init__(self):
        self.client: DockerClient = docker.from_env()
        self.jobs: list[ControllerJob] = []

    def job_create(self, job_enum: JobEnum, initial_cores: list[str], initial_threads: int) -> None:
        controller_job = ControllerJob(job_enum)
        logger.info(
            f"Starting {str(job_enum)} container with {initial_cores} cores and {initial_threads} threads. Image: {controller_job.image}"
        )
        container = self.client.containers.run(
            controller_job.image,
            detach=True,
            remove=True,
            cpuset_cpus=",".join(initial_cores),
            name=job_enum.value,
            command=controller_job._run_command(initial_threads),
        )
        controller_job._set_container(container)
        self.jobs.append(controller_job)
        logger.info(f"Started {str(controller_job)} container with id {controller_job.container.short_id}")

    #  TODO : MOVE TO CONTROLLERJOB
    def job_end(self, job: Union[ControllerJob, JobEnum]) -> None:
        job = self.extract_job(job)
        logger.info(f"Ending {str(job)} container with id {job.container.short_id}")
        job.container.stop()
        self.jobs.remove(job)

    def job_update_cores(self, job: Union[ControllerJob, JobEnum], cores: list[str]) -> None:
        job = self.extract_job(job)
        logger.info(f"Updating {str(job)} container with cores {cores}")
        job.container.update(cpuset_cpus=",".join(cores))

    def job_pause(self, job: Union[ControllerJob, JobEnum]) -> None:
        job = self.extract_job(job)
        logger.info(f"Pausing {str(job)} container with id {job.container.short_id}")
        job.container.pause()

    def job_unpause(self, job: Union[ControllerJob, JobEnum]) -> None:
        job = self.extract_job(job)
        logger.info(f"Unpausing {str(job)} container with id {job.container.short_id}")
        job.container.unpause()

    def extract_job(self, job: Union[ControllerJob, JobEnum]) -> ControllerJob:
        if isinstance(job, JobEnum):
            for controller_job in self.jobs:
                if controller_job.job == job:
                    job = controller_job
                    break
        return job

    # TODO : END MOVE

    def monitor_container_cpu(self):
        for job in self.jobs:
            stats = job.container.stats(stream=False)
            cpu_percent = stats["cpu_stats"]["cpu_usage"]["total_usage"] / stats["cpu_stats"]["system_cpu_usage"] * 100
            logger.info(f"{str(job)} container CPU usage: {cpu_percent:.2f}%")

    def monitor_system_stats(self):
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        logger.info(f"System CPU usage: {cpu_percent:.2f}%")
        logger.info(f"System memory usage: {str(memory)}.")
        return cpu_percent, memory

    def system_overloaded(self, cpu_threshold: float = 90) -> bool:
        cpu_percent, memory = self.monitor_system_stats()
        return cpu_percent < cpu_threshold

    def schedule_loop(self):
        # TODO : Implement the scheduling loop in a
        while True:
            if self.system_overloaded(90):
                for job in self.jobs:
                    self.job_pause(job)  # TODO : do more fancy stuff here - update cores, etc.
            elif not self.system_overloaded(50):
                for job in self.jobs:
                    self.job_unpause(job)  # TODO : do more fancy stuff here - update cores, etc.
            time.sleep(0.1)
