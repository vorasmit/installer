# main file for task selection
from utils import *

"""
This file will be executed on the server after the server is created.

Requirements:
=============
1. Python 3.6 or above
2. Git
3. Tested on Ubuntu 22.04

Steps for Running This Script:
==============================
1. Create a new user on the server (make sure its same as the username in config.json)
2. Add the user to sudoers
3. Login as the new user
4. Install git
5. Clone this repo
6. Go to the repo directory
7. Run this script after updating the config.json file

eg for a new user named `frappe`
```sh
sudo adduser frappe
sudo usermod -aG sudo frappe
su - frappe

sudo apt-get update && sudo apt-get install git -y
git clone https://github.com/vorasmit/installer.git
cd installer/scripts/new_setup
python3 main.py
```

"""
if __name__ == "__main__":
    while True:
        print("Select Task", end="\n\n\n")
        task_list = {
            "Update Server Config": update_server_config,
            "Update System for MariaDB": update_system_for_mariadb,
            "Install Bench": install_bench,
            "Initialize Bench with Apps": intialize_bench_with_apps,
            "Create Site with App": create_site_with_app,
            "Setup SSL": setup_ssl,
            "Setup Production": setup_production_server,
        }

        for key, value in enumerate(task_list.items()):
            print(f"{key + 1}. {value[0]}")

        print("Enter 'q' to quit")
        task = input("\n\nEnter the task number: ")

        try:
            if task == "q":
                break
            task_list[list(task_list.keys())[int(task) - 1]]()
        except Exception as e:
            print(e)
