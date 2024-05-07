import time
import psutil
from datetime import datetime


if __name__ == "__main__":
    for _ in range(40):

        cpu_usage = psutil.cpu_percent(percpu=True)
        print(f"{datetime.now().isoformat()} {cpu_usage[0]} {cpu_usage[1]} {cpu_usage[2]} {cpu_usage[3]}", flush=True)

        time.sleep(5)
