from utils import *
import os
from loguru import logger

def task4():    
    target = "memcache-server"
    requirements = "requirements_part4.txt"
    source_folder = os.join(".", "scripts")
    destination = os.join("~")
    for file_name in os.listdir(source_folder):
        if ((file_name.startswith("task4") and file_name.endswith(".py")) \
            or (file_name == "utils.py") \
            or (file_name == requirements)):
          source_file = os.join(source_folder, file_name)
          copy_file_to_node(target, source_file, destination)

    logger.info(f"Copied python scripts to {target}")

    ssh_command(target, f"pip install -r {requirements}")

    logger.info(f"Installed requirements to {target}")


if __name__ == "__main__":
    task4()