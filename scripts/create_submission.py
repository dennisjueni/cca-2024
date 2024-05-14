from scripts.utils import Part
import os
import shutil


def copy_measurement_files_part3():
    source_directories = [
        "results-part3/final_runs/run1",
        "results-part3/final_runs/run2",
        "results-part3/final_runs/run3",
    ]
    destination_directory = "submission/part_3_results_group_076"

    for idx, source_directory in enumerate(source_directories):
        # Get the list of files in the source directory
        files = os.listdir(source_directory)

        # Iterate over the files and copy them to the destination directory with a new name
        for file in files:

            if file == "results.json":
                new_name = f"pods_{idx+1}.json"
                shutil.copy(os.path.join(source_directory, file), os.path.join(destination_directory, new_name))
            elif file == "mcperf.txt":
                new_name = f"mcperf_{idx+1}.txt"
                with open(os.path.join(source_directory, file), "r") as source_file:
                    with open(os.path.join(destination_directory, new_name), "w") as destination_file:
                        for line in source_file:
                            if len(line) == 176:
                                destination_file.write(line)


def copy_yaml_files_part3():
    os.makedirs(f"submission/yaml_files_part3", exist_ok=True)
    source_directory = "yaml_files_part3"

    for file in os.listdir(source_directory):
        shutil.copy(os.path.join(source_directory, file), f"submission/yaml_files_part3/{file}")


def copy_scripts_part3():
    os.makedirs(f"submission/scripts", exist_ok=True)

    shutil.copy("scripts/task3.py", f"submission/scripts/task3.py")
    shutil.copy("scripts/job.py", f"submission/scripts/job.py")
    shutil.copy("scripts/utils.py", f"submission/scripts/utils.py")
    shutil.copy("scripts/delete.py", f"submission/scripts/delete.py")

    shutil.copy("get_time.py", f"submission/scripts/get_time.py")


def copy_measurement_files_part4(interval: int):
    source_directories = [
        f"results-part4/part2_final_runs/int{interval}_run0",
        f"results-part4/part2_final_runs/int{interval}_run1",
        f"results-part4/part2_final_runs/int{interval}_run2",
    ]
    if interval == 10:
        destination_directory = "submission/part_4_3_results_group_076"
    elif interval == 1:
        destination_directory = "submission/part_4_4_results_group_076"
    else:
        raise ValueError("Invalid interval")

    for idx, source_directory in enumerate(source_directories):
        # Get the list of files in the source directory
        files = os.listdir(source_directory)

        # Iterate over the files and copy them to the destination directory with a new name
        for file in files:

            if file == "log.txt":
                new_name = f"jobs_{idx+1}.txt"
                shutil.copy(os.path.join(source_directory, file), os.path.join(destination_directory, new_name))
            elif file == "mcperf.txt":
                new_name = f"mcperf_{idx+1}.txt"
                with open(os.path.join(source_directory, file), "r") as source_file:
                    with open(os.path.join(destination_directory, new_name), "w") as destination_file:
                        for line in source_file:
                            if len(line) == 146:
                                destination_file.write(line)


def copy_scripts_part4():

    shutil.copy("scripts/task4_config.py", f"submission/scripts/task4_config.py")
    shutil.copy("scripts/task4_controller.py", f"submission/scripts/task4_controller.py")
    shutil.copy("scripts/task4_cpu.py", f"submission/scripts/task4_cpu.py")
    shutil.copy("scripts/task4_job.py", f"submission/scripts/task4_job.py")
    shutil.copy("scripts/task4_scheduler_logger.py", f"submission/scripts/task4_scheduler_logger.py")
    shutil.copy("scripts/task4.py", f"submission/scripts/task4.py")


def create_submission(parts: list[Part] = [Part.PART3, Part.PART4]):

    # Create the submission folder
    os.makedirs("submission", exist_ok=True)

    if Part.PART3 in parts:
        os.makedirs(f"submission/part_3_results_group_076", exist_ok=True)

        copy_measurement_files_part3()
        copy_yaml_files_part3()
        copy_scripts_part3()

    if Part.PART4 in parts:
        os.makedirs(f"submission/part_4_3_results_group_076", exist_ok=True)
        os.makedirs(f"submission/part_4_4_results_group_076", exist_ok=True)

        copy_scripts_part4()
        copy_measurement_files_part4(10)
        copy_measurement_files_part4(1)

    print("!!! DO NOT FORGET TO INCLUDE THE REPORT IN THE SUBMISSION !!!")


if __name__ == "__main__":
    create_submission()
