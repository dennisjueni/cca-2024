from datetime import datetime
import urllib.parse

from task4_config import JobEnum


LOG_STRING = "{timestamp} {event} {job_name} {args}"


class SchedulerLogger:
    def __init__(self):
        start_date = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.file = open(f"log{start_date}.txt", "w")
        self._log("start", JobEnum.SCHEDULER)

    def _log(self, event: str, job_name: JobEnum, args: str = "") -> None:
        self.file.write(
            LOG_STRING.format(
                timestamp=datetime.now().isoformat(), event=event, job_name=job_name.value, args=args
            ).strip()
            + "\n"
        )

    def job_start(self, job: JobEnum, initial_cores: list[int], initial_threads: int) -> None:
        assert job != JobEnum.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("start", job, "[" + (",".join(str(i) for i in initial_cores)) + "] " + str(initial_threads))

    def job_end(self, job: JobEnum) -> None:
        assert job != JobEnum.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("end", job)

    def update_cores(self, job: JobEnum, cores: list[int]) -> None:
        assert job != JobEnum.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("update_cores", job, "[" + (",".join(str(i) for i in cores)) + "]")

    def job_pause(self, job: JobEnum) -> None:
        assert job != JobEnum.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("pause", job)

    def job_unpause(self, job: JobEnum) -> None:
        assert job != JobEnum.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("unpause", job)

    def custom_event(self, job: JobEnum, comment: str):
        self._log("custom", job, urllib.parse.quote_plus(comment))

    def end(self) -> None:
        self._log("end", JobEnum.SCHEDULER)
        self.file.flush()
        self.file.close()
