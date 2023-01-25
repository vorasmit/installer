#!/usr/bin/env python

import shutil
import os
import json
import pwd


def print_step(step):
    print("")
    print("\033[92m" + step + "\033[0m")


def read_server_script_json():
    with open("config.json", "r") as f:
        return json.load(f)


def update_config(config, file):
    """
    This function will update the config to the end of the file if it doesn't exist
    """

    with open(file, "r") as f:
        for line in f:
            if line.startswith(config):
                return

    os.system(f'echo "{config}" | sudo tee -a {file}')


def add_authorized_keys(username, keys):
    print_step("Adding authorized keys")

    if not keys:
        return

    os.system("mkdir /home/" + username + "/.ssh")
    filename = "/home/" + username + "/.ssh/authorized_keys"
    if not os.path.exists(filename):
        os.system("touch " + filename)

    for name, key in keys.items():
        update_config(f"# {name}", filename)
        update_config(key, filename)
        update_config(" ", filename)

    change_permissions_for_ssh(username)


def change_permissions_for_ssh(username):
    os.system("chown -R " + username + ":" + username + " /home/" + username + "/.ssh")
    os.system("chmod 700 /home/" + username + "/.ssh")
    os.system("chmod 644 /home/" + username + "/.ssh/authorized_keys")


def update_ssh_config(port):
    """
    Update ssh config to disable root login and change port if needed
    """
    print_step("Updating ssh config")

    filename = "/etc/ssh/sshd_config"
    if port and port != 22:
        update_config(f"Port {port}", filename)

    update_config("PermitRootLogin no", filename)
    os.system("sudo systemctl restart ssh")


def update_sysctl_config():
    """
    Update sysctl config for better mariadb performance.
    Reference: https://www.digitalocean.com/community/tutorials/how-to-add-swap-space-on-ubuntu-22-04

    1. Set minimal priority for swappiness
    2. Update vfs cache pressure to 50 for better performance
    """
    print_step("Updating sysctl config")

    filename = "/etc/sysctl.conf"
    update_config("vm.swappiness=1", filename)
    update_config("vm.vfs_cache_pressure=50", filename)


def set_io_scheduler_to_none():
    """
    Set IO scheduler to none for better mariadb performance
    Reference: https://mariadb.com/kb/en/configuring-linux-for-mariadb/
    """

    # TODO: harddisk drive name is hardcoded
    # TODO: replace existing scheduler with none. This will append.
    os.system("echo none | sudo tee /sys/block/sda/queue/scheduler")


# def create_swap_partition():
#     # check existing swap
#     if os.system('swapon -s') == 0:
#         return

#     # create swap partition
#     os.system('sudo fallocate -l 4G /swapfile')
#     os.system('sudo chmod 600 /swapfile')
#     os.system('sudo mkswap /swapfile')
#     os.system('sudo swapon /swapfile')


######################################################################

# Install required packages


def install_dependencies(dependencies):
    install_python(dependencies["python"])
    install_mariadb(dependencies["mariadb"])
    install_nodejs(dependencies["node"])
    install_wkhtmltopdf(dependencies["wkhtmltopdf"])
    install_other_dependencies()


def install_python(version):
    print_step("Installing python " + version)

    python = "python" + version
    os.system("sudo add-apt-repository ppa:deadsnakes/ppa -y && sudo apt-get update")
    os.system(
        f"sudo apt-get install {python} {python}-dev {python}-venv python3-pip python3-setuptools -y"
    )


def install_mariadb(version):
    print_step("Installing mariadb " + version)

    os.system(
        "wget -O - https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | sudo bash"
    )
    os.system(
        f"sudo apt-get install mariadb-server={version} mariadb-client={version} libmysqlclient-dev -y"
    )

    mysql_secure_installation()
    # TODO: update mariadb config
    update_mariadb_config()


def mysql_secure_installation():
    os.system("sudo mysql_secure_installation")


def update_mariadb_config():
    """
    Create config files:
    1. /etc/mysql/mariadb.conf.d/erpnext.cnf
    2. /etc/systemd/system/mariadb.service.d/override.conf
    """
    print_step("Updating mariadb config")

    # create config file
    os.system("sudo mkdir -p /etc/mysql/mariadb.conf.d")
    os.system("sudo touch /etc/mysql/mariadb.conf.d/erpnext.cnf")

    # update config file

    pass


def install_nodejs(version):
    print_step("Installing nodejs " + version)

    os.system("sudo apt-get install curl -y")
    os.system(
        "curl -sL https://deb.nodesource.com/setup_" + version + ".x | sudo -E bash -"
    )
    os.system("sudo apt-get install nodejs -y")


def install_wkhtmltopdf(info):
    """
    Manual installation of wkhtmltopdf
    Reference: https://wkhtmltopdf.org/downloads.html
    """
    print_step("Installing wkhtmltopdf " + info["version"])

    os.system(
        f'wget https://github.com/wkhtmltopdf/packaging/releases/download/{info["version"]}/{info["filename"]}'
    )
    os.system(f'sudo apt-get install ./{info["filename"]} -y')
    os.system(f'rm {info["filename"]}')


def install_other_dependencies():
    # yarn
    print_step("Installing yarn")
    os.system("npm install -g yarn")

    # redis-server
    print_step("Installing redis-server")
    os.system("sudo apt-get install redis-server -y")

    # install git
    print_step("Installing git")
    os.system("sudo apt-get install git -y")


######################################################################


if __name__ == "__main__":
    server_script = read_server_script_json()
    username = server_script["username"]

    add_authorized_keys(username, server_script["authorized_keys"])
    update_ssh_config(server_script.get("ssh_port"))
    update_sysctl_config()
    # set_io_scheduler_to_none()

    # TODO: work on this
    # create_swap_partition()

    install_dependencies(server_script["dependencies"])

    os.system("exit")
