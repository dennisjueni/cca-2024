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
from task4_job import ControllerJob
from task4_config import *
from docker.client import DockerClient
import psutil


class Controller:
    def __init__(self):
        self.client: DockerClient = docker.from_env()
        self.jobs: list[ControllerJob] = []

    def create_container(
        self, image: str, command: str, name: str, cpuset_cpus: str = "0", **kwargs
    ) -> docker.models.containers.Container:
        kwargs["detach"] = kwargs.get("detach", True)
        kwargs["remove"] = kwargs.get("remove", True)
        container = self.client.containers.run(
            image,
            cpuset_cpus=cpuset_cpus,
            name=name,
            command=command,
            **kwargs,
        )
        return container

    def job_create(self, job_enum: JobEnum, initial_cores: list[str], nr_threads: int) -> None:
        controller_job = ControllerJob(job_enum)
        logger.info(
            f"Starting {str(job_enum)} container with {initial_cores} cores and {nr_threads} threads. Image: {controller_job.image}"
        )
        container = self.create_container(
            controller_job.image,
            command=controller_job._run_command(nr_threads),
            name=controller_job.job.value,
        )
        controller_job._set_container(container)
        self.jobs.append(controller_job)
        logger.info(f"Started {str(controller_job)} container with id {controller_job.container.short_id}")

    def create_jobs(self):
        for job in JobEnum:
            self.job_create(job, initial_cores="0", nr_threads=3)  # TODO : Threads ?

    def extract_job(self, job: Union[JobEnum, ControllerJob]) -> ControllerJob:
        assert isinstance(job, JobEnum) or isinstance(job, ControllerJob), f"Invalid job type: {type(job)}"
        if isinstance(job, JobEnum):
            for controller_job in self.jobs:
                if controller_job.job == job:
                    job = controller_job
                    break
        return job

    def monitor_container_cpu(self):
        for job in self.jobs:
            stats = job.container.stats(stream=False)
            logger.info(f"Stats for {str(job)} container: {stats}")
            cpu_percent = stats["cpu_stats"]["cpu_usage"]["total_usage"] / stats["cpu_stats"]["system_cpu_usage"] * 100
            logger.info(f"{str(job)} container CPU usage: {cpu_percent:.2f}%")

    def monitor_system_stats(self):
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        logger.info(f"System CPU usage: {cpu_percent:.2f}%")
        logger.info(f"System memory usage: {str(memory)}.")
        return cpu_percent, memory

    def is_system_overloaded(self, cpu_threshold: float = 90) -> bool:
        cpu_percent, memory = self.monitor_system_stats()
        return cpu_percent < cpu_threshold

    def schedule_loop(self):
        # TODO : Implement the scheduling loop in a
        while True:
            for job in self.jobs:
                if job.has_finished():
                    job.end()
                    self.jobs.remove(job)
            if self.is_system_overloaded(80):
                for job in self.jobs:
                    if not job.is_paused:
                        logger.info(f"Pausing {str(job)} container with id {job.container.short_id}")
                        job.pause()
                        break
            else:
                for job in self.jobs:  # only run one job at a time
                    if job.is_paused:
                        job.unpause()
                        break
                    if len(job._get_cores()) < psutil.cpu_count():
                        job.add_core()
                        break
            if len(self.jobs) == 0:
                logger.info("No jobs running. Exiting scheduling loop.")
                break
            time.sleep(0.1)
