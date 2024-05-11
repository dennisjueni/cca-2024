"""
This python script should run alongside `memcached` on 
"""

import time
import docker
import docker.models
import docker.models.containers
from docker.client import DockerClient
import psutil
import subprocess
from loguru import logger
from collections import deque

from task4_scheduler_logger import SchedulerLogger
from task4_job import ControllerJob
from task4_config import JobEnum


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
        self.num_memcached_cores = 2
        self.logger = SchedulerLogger()
        self.measurement_list = deque(maxlen=10)

    def start_controlling(self):
        # Start memcached on core 0, do not use the set_memcached_cores function since we do not want to log the update_cores here
        self.logger.job_start(JobEnum.MEMCACHED, initial_cores=[0, 1], initial_threads=2)
        taskset_command = f"sudo taskset -a -c 0,1 -p {self.memcached_pid}"
        subprocess.run(taskset_command.split())

        self.create_jobs()
        self.schedule_loop()

    def set_memcached_cores(self, cores: list[int]):
        if len(cores) == self.num_memcached_cores:
            return
        self.measurement_list.clear()
        self.num_memcached_cores = len(cores)
        taskset_command = f"sudo taskset -a -c {','.join(list(map(str, cores)))} -p {self.memcached_pid}"
        subprocess.run(taskset_command.split())
        self.logger.update_cores(JobEnum.MEMCACHED, cores=cores)

    def job_create(self, job_enum: JobEnum) -> None:
        controller_job = ControllerJob(job_enum, client=self.client, logger=self.logger)

        logger.info(f"Creating {str(job_enum)}-container with image: {controller_job.image}")

        controller_job.create_container()

        self.jobs.append(controller_job)
        logger.info(f"Created {str(controller_job)} container with id {controller_job.container.short_id}")

    def create_jobs(self):
        for job in JobEnum:
            if job == JobEnum.MEMCACHED or job == JobEnum.SCHEDULER:
                continue
            self.job_create(job)

    def is_memcached_overloaded(self, cpu_threshold) -> bool:
        cpu_percent = psutil.cpu_percent(percpu=True)

        if cpu_percent[0] == 0.0 or (self.num_memcached_cores == 2 and cpu_percent[1] == 0.0):
            return False

        if self.num_memcached_cores == 1:
            self.measurement_list.append(cpu_percent[0])
        else:
            self.measurement_list.append(cpu_percent[0] + cpu_percent[1])

        if len(self.measurement_list) < 5:
            return False

        return sum(self.measurement_list) / len(self.measurement_list) > cpu_threshold

    def is_memcached_underloaded(self, cpu_threshold) -> bool:
        cpu_percent = psutil.cpu_percent(percpu=True)

        if cpu_percent[0] == 0.0 or (self.num_memcached_cores == 2 and cpu_percent[1] == 0.0):
            return False

        if self.num_memcached_cores == 1:
            self.measurement_list.append(cpu_percent[0])
        else:
            self.measurement_list.append(cpu_percent[0] + cpu_percent[1])

        if len(self.measurement_list) < 5:
            return False

        return sum(self.measurement_list) / len(self.measurement_list) < cpu_threshold

    def schedule_loop(self):
        OVERLOADED_THRESHOLD = 70
        UNDERLOADED_THRESHOLD = 100

        current_job = self.jobs.pop(0)
        current_job.start_container()

        while True:
            curr_job_finished = current_job.is_finished()

            if curr_job_finished:
                if len(self.jobs) == 0:
                    # This means we have finished all jobs and we can thus break the loop and let memcached run alone
                    self.set_memcached_cores([0, 1])
                    break

                # This means we can start the next job in the list and run it
                current_job = self.jobs.pop(0)
                current_job.start_container()

                if self.num_memcached_cores == 1:
                    current_job.update_cores([1, 2, 3])
            else:
                if self.num_memcached_cores == 1 and self.is_memcached_overloaded(OVERLOADED_THRESHOLD):
                    self.set_memcached_cores([0, 1])
                    current_job.update_cores([2, 3])

                elif self.num_memcached_cores == 2 and self.is_memcached_underloaded(UNDERLOADED_THRESHOLD):
                    self.set_memcached_cores([0])
                    current_job.update_cores([1, 2, 3])

            time.sleep(0.1)

        time.sleep(60)
        self.logger.job_end(JobEnum.MEMCACHED)


if __name__ == "__main__":
    controller = Controller()
    controller.start_controlling()
