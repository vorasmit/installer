#!/usr/bin/env python

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
python3 server_script.py
```

"""

import os
import json


def print_step(step):
    print("")
    print("\033[92m" + step + "\033[0m")


def update_and_upgrade_apt():
    print_step("Updating and upgrading apt packages")
    os.system("sudo apt-get update && sudo apt-get upgrade -y")


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


def set_io_scheduler_to_none(device_name=None):
    """
    Set IO scheduler to none for better mariadb performance
    Reference: https://mariadb.com/kb/en/configuring-linux-for-mariadb/
    """
    if not device_name:
        # show all devices
        all_devices = os.listdir("/sys/block")
        print(all_devices)
        while True:
            device_name = input("Enter device name (e.g. sda): ")
            if device_name in all_devices:
                break
            print("Invalid device name. Please try again.")
    os.system(f"echo none | sudo tee /sys/block/{device_name}/queue/scheduler")


def create_swap_partition(swap_size=None):
    """
    Create swap partition
    Reference: https://www.digitalocean.com/community/tutorials/how-to-add-swap-space-on-ubuntu-22-04
    Appropriate swap size: https://help.ubuntu.com/community/SwapFaq#How_much_swap_do_I_need.3F
    """
    print_step("Creating swap partition")
    if not swap_size or not swap_size.isdigit():
        # show device size
        os.system("free -h")
        while True:
            swap_size = input("Enter swap size (e.g. 1): ")
            if swap_size.isdigit():
                break
            print("Invalid swap size. Please try again.")
    os.system(f"sudo fallocate -l {swap_size}G /swapfile")
    os.system("sudo chmod 600 /swapfile")
    os.system("sudo mkswap /swapfile")
    os.system("sudo swapon /swapfile")
    os.system("sudo cp /etc/fstab /etc/fstab.bak")
    os.system("echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab")


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
    os.system("wget https://downloads.mariadb.com/MariaDB/mariadb_repo_setup")
    os.system("chmod +x mariadb_repo_setup")
    os.system(f"sudo ./mariadb_repo_setup --mariadb-server-version='{version}'")
    os.system(
        f"sudo apt-get install mariadb-server-{version} mariadb-client-{version} libmysqlclient-dev -y"
    )
    os.system("rm mariadb_repo_setup")

    mysql_secure_installation()
    update_mariadb_config()


def mysql_secure_installation():
    os.system("sudo mysql_secure_installation")


def update_mariadb_config(innodb_buffer_pool_size=None):
    """
    Create config files:
    1. /etc/mysql/mariadb.conf.d/erpnext.cnf
    2. /etc/systemd/system/mariadb.service.d/override.conf
    """
    print_step("Updating mariadb config")

    # update erpnext.cnf
    create_erpnect_cnf(innodb_buffer_pool_size)

    # update override.conf
    dir = "/etc/systemd/system/mariadb.service.d"
    filename = "override.conf"
    file_path = os.path.join(dir, filename)

    os.system(f"sudo mkdir -p {dir}")
    if not os.path.exists(file_path):
        os.system(f"sudo touch {file_path}")

    update_config("[Service]", file_path)
    update_config("LimitNOFILE=infinity", file_path)
    update_config("LimitCORE=infinity", file_path)

    os.system("sudo systemctl daemon-reload")

    # restart mariadb
    os.system("sudo systemctl restart mariadb")


def install_nodejs(version):
    print_step("Installing nodejs " + version)

    os.system("sudo apt-get install curl -y")
    os.system(
        "curl -sL https://deb.nodesource.com/setup_"
        + version
        + " -o nodesource_setup.sh"
    )
    os.system("sudo bash nodesource_setup.sh")
    os.system("sudo apt-get install nodejs -y")
    os.system("rm nodesource_setup.sh")


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
    os.system("sudo npm install -g yarn")

    # redis-server
    print_step("Installing redis-server")
    os.system("sudo apt-get install redis-server -y")

    # install git
    print_step("Installing git")
    os.system("sudo apt-get install git -y")


#######################################################################
# Install frappe-bench ################################################
#######################################################################


def install_frappe_bench():
    print_step("Installing latest frappe-bench")
    os.system("sudo pip3 install frappe-bench")
    os.system("bench --version")


def intialize_frappe_bench(username, version, apps, bench_name):
    print_step("Initializing frappe-bench")
    # install frappe with python version and branch

    os.chdir(f"/home/{username}")
    for app in apps:
        if app == "frappe":
            branch = apps[app]["branch"]
            break

    os.system(
        f"bench init --frappe-branch {branch} --python python{version} {bench_name}"
    )
    os.chdir(f"/home/{username}/{bench_name}")
    get_apps(apps)


def get_apps(apps):
    print_step("Getting apps")

    for app in apps:
        if app != "frappe":
            os.system(
                f"bench get-app --branch {apps[app]['branch']} {apps[app]['url']}"
            )


def setup_site(site_name, mariadb_root_password, admin_password, apps, dns_multitenant):
    print_step(f"Setting up site {site_name}")

    os.system(
        f"bench new-site {site_name} --mariadb-root-password {mariadb_root_password} --admin-password {admin_password}"
    )
    for app in apps:
        if app != "frappe":
            os.system(f"bench --site {site_name} install-app {app}")

    os.system(f"bench set-config dns_multitenant {dns_multitenant}")


#######################################################################
# Setup production ####################################################
#######################################################################


def setup_production(username, bench_name):
    print_step("Setting up production")
    os.chdir(f"/home/{username}/{bench_name}")
    os.system(f"sudo bench setup production --yes {username}")
    supervisorctl_permissions(username)
    os.system("sudo systemctl restart supervisor")


def supervisorctl_permissions(username):
    # add www-data to sudoers
    os.system(f"sudo usermod -a -G {username} www-data")

    # add these lines under [unix_http_server] in /etc/supervisor/supervisord.conf
    filepath = "/etc/supervisor/supervisord.conf"
    data = f"""
    chmod=0770\n
    chown={username}:{username}
    """
    os.system(f"sudo sed -i '6i {data}' {filepath}")


def install_certbot():
    print_step("Installing certbot")
    os.system("sudo apt install snapd")
    os.system("sudo snap install --classic certbot")


def generate_ssl_certificate(site_name, ssl_email):
    print_step("Generating SSL")
    os.system(
        f"sudo certbot --nginx -d {site_name} -d www.{site_name} --non-interactive --agree-tos --email {ssl_email}"
    )


def add_ssl_to_site(site_name, username, bench_name):
    print_step("Adding SSL to site")
    if not os.path.exists("/etc/letsencrypt/live/"):
        print("SSL certificate not found")
        return
    fullchain = f"/etc/letsencrypt/live/{site_name}/fullchain.pem"
    privkey = f"/etc/letsencrypt/live/{site_name}/privkey.pem"

    os.chdir(f"/home/{username}/{bench_name}")
    os.system(f"bench set-config ssl_certificate {fullchain}")
    os.system(f"bench set-config ssl_certificate_key {privkey}")
    os.system(f"sudo systemctl restart nginx")


#######################################################################
# erpnext.cnf############################################################
#######################################################################


def create_erpnect_cnf(innodb_buffer_pool_size=None):
    # create erpnext.cnf file
    print_step("Creating erpnext.cnf file")
    # create file
    dir = "/etc/mysql/mariadb.conf.d"
    filename = "erpnext.cnf"
    os.system(f"sudo mkdir -p {dir}")
    os.system(f"sudo touch {dir}/{filename}")
    file_path = f"{dir}/{filename}"
    # calculate innodb_buffer_pool_size
    if innodb_buffer_pool_size is None or innodb_buffer_pool_size == 0:
        innodb_buffer_pool_size = calculate_innodb_buffer_pool_size()
    data = f"""
    [mysqld]

    # GENERAL #
    user                           = mysql
    default-storage-engine         = InnoDB
    # socket                         = /var/lib/mysql/mysql.sock
    # pid-file                       = /var/lib/mysql/mysql.pid

    # MyISAM #
    key-buffer-size                = 32M
    myisam-recover                 = FORCE,BACKUP

    # SAFETY #
    max-allowed-packet             = 256M
    max-connect-errors             = 1000000
    innodb                         = FORCE

    # DATA STORAGE #
    datadir                        = /var/lib/mysql/

    # BINARY LOGGING #
    log-bin                        = /var/lib/mysql/mysql-bin
    expire-logs-days               = 14
    sync-binlog                    = 1

    # REPLICATION #
    server-id                      = 1

    # CACHES AND LIMITS #
    tmp-table-size                 = 32M
    max-heap-table-size            = 32M
    query-cache-type               = 0
    query-cache-size               = 0
    max-connections                = 500
    thread-cache-size              = 50
    open-files-limit               = 65535
    table-definition-cache         = 4096
    table-open-cache               = 10240

    # INNODB #
    innodb-flush-method            = O_DIRECT
    innodb-log-files-in-group      = 2
    innodb-log-file-size           = 512M
    innodb-flush-log-at-trx-commit = 1
    innodb-file-per-table          = 1
    innodb-buffer-pool-size        = {innodb_buffer_pool_size}M
    innodb-file-format             = barracuda
    innodb-large-prefix            = 1
    collation-server               = utf8mb4_unicode_ci
    character-set-server           = utf8mb4
    character-set-client-handshake = FALSE
    max_allowed_packet             = 256M

    # LOGGING #
    log-error                      = /var/lib/mysql/mysql-error.log
    log-queries-not-using-indexes  = 0
    slow-query-log                 = 1
    slow-query-log-file            = /var/lib/mysql/mysql-slow.log

    [mysql]
    default-character-set = utf8mb4

    [mysqldump]
    max_allowed_packet=256M
    """
    update_config(data, file_path)


def calculate_innodb_buffer_pool_size():
    # calculate innodb buffer pool size
    print_step("Calculating innodb buffer pool size")
    free_memory = os.popen("free -m | awk '/^Mem:/{print $4}'").read()
    innodb_buffer_pool_size = int(free_memory * 0.6)
    # convert value to whole number
    return innodb_buffer_pool_size


######################################################################


if __name__ == "__main__":
    config = read_server_script_json()
    username = config["username"]

    update_and_upgrade_apt()
    add_authorized_keys(username, config["authorized_keys"])
    update_ssh_config(config.get("ssh_port"))
    update_sysctl_config()

    set_io_scheduler_to_none()
    create_swap_partition(config["swap_size"])

    install_dependencies(config["dependencies"])

    # init frappe-bench
    install_frappe_bench()
    intialize_frappe_bench(
        username, config["dependencies"]["python"], config["apps"], config["bench_name"]
    )
    setup_site(
        config["site_name"],
        config["mariadb_root_password"],
        config["admin_password"],
        config["apps"],
        config["dns_multitenant"],
    )

    os.system("exit")
