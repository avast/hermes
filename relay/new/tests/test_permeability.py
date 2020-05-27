from __future__ import print_function
import os
os.environ["SALMON_SETTINGS_MODULE"] = "testing_settings"
os.environ["PERMEABILITY_ENV"] = "1"
import logging
import logging.config
logging.getLogger("paramiko").setLevel(logging.WARNING)
from salmon import utils
from salmon.salmonmailparser import process_email
from salmon.mail import MailRequest
from salmon.salmondb import get_statistics
from salmon.salmondb import Settings
from salmon.salmondb import push_into_db
from salmon.salmonconclude import conclude
from prettytable import PrettyTable
import sys
import argparse
from paramiko import SSHClient
from scp import SCPClient
from pathlib import Path
import shutil
from datetime import datetime
from datetime import timedelta
import time
import glob


RELAYED = 0
HOUR = -1


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def parse_arguments():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "-n",
        type=int,
        help="number of eml files from the directory, "
        "in case you want to test for example only 100 newest",
    )
    required = parser.add_argument_group("required")
    required.add_argument(
        "--path",
        "-p",
        type=str,
        help='path to a directory with eml files without last "/", e.g. /home',
    )
    clean = parser.add_argument_group("clean up")
    clean.add_argument("--clean", action="store_true", help="clean up after tests")
    group = parser.add_argument_group("ssh connection")
    group.add_argument(
        "--scp", action="store_true", help="use scp to get the eml files"
    )
    group.add_argument("--password", type=str, help="password for ssh connection")
    group.add_argument("--username", type=str, help="username for ssh connection")
    group.add_argument("--hostname", type=str, help="hostname")
    group.add_argument("--port", default=22, type=int, help="port where to connect")
    args = parser.parse_args()

    if args.scp and (not args.password or not args.username or not args.hostname):
        eprint("password, username and hostname are required if you want to use scp")
    elif not args.scp and (args.password or args.username or args.hostname):
        eprint("use --scp if you want to use scp")
    return args


def use_scp(args):
    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.connect(
        hostname=args.hostname,
        port=args.port,
        username=args.username,
        password=args.password,
    )

    files = []
    scp = SCPClient(ssh.get_transport())
    command = "ls -t {directory}".format(directory=args.path)
    (stdin, stdout, stderr) = ssh.exec_command(command)
    for line in stdout.readlines():
        files.append(line.strip("\n"))
    scp.close()

    if args.n:
        files = files[: args.n]

    while files:
        files_ready_for_test = []
        mtimes = {}
        scp = SCPClient(ssh.get_transport())
        for i in range(300):
            try:
                f = files.pop()
            except IndexError as e:
                break
            else:
                command_mtime = "echo `stat -c %Y -- {directory}/{file}`".format(
                    directory=args.path, file=f
                )
                (stdin, stdout, stderr) = ssh.exec_command(command_mtime)
                for line in stdout.readlines():
                    mtimes[f] = line.strip("\n")
                    t = int(line.strip("\n"))
                    global HOUR
                    if HOUR == -1:
                        update_hour(t)
                    elif t >= HOUR:
                        update_hour(t)
                        RELAYED = 0
                scp.get(
                    remote_path=args.path + "/" + f,
                    local_path="./queue/new/{}".format(f),
                )
                files_ready_for_test.append(f)
        scp.close()
        run(files_ready_for_test, "queue/new", mtimes)


def read_from_dir(args):
    files = glob.glob("*")
    files.sort(key=os.path.getmtime, reverse=True)
    if args.n:
        files = files[: args.n]

    while files:
        files_ready_for_test = []
        mtimes = {}
        for i in range(300):
            try:
                f = files.pop()
            except IndexError as e:
                break
            else:
                t = int(time = os.path.getmtime(f))
                mtimes[f] = t
                global HOUR
                if HOUR == -1:
                    update_hour(t)
                elif t >= HOUR:
                    update_hour(t)
                    RELAYED = 0
                shutil.copy(args.path + "/" + f, "./queue/new/{}".format(f))
                files_ready_for_test.append(f)
        run(files_ready_for_test, "queue/new", mtimes)
        time.sleep(5)


def update_hour(t):
    HOUR = int(
        datetime.timestamp(
            (datetime.fromtimestamp(t) + timedelta(hours=1))
        )
    )


def eml_content(file_name, directory):
    with open("./{0}/{1}".format(directory, file_name), "rb") as f:
        content = f.read()
    return content


def run(files, directory, mtimes):
    mail_fields = None
    for file_name in files:
        mail_request = MailRequest(
            file_name, None, None, eml_content(file_name, directory)
        )
        mail_fields = process_email(file_name, mail_request)
        if mail_fields:
            mtime = mtimes[file_name]
            mail_fields["date"] = mtime
            rating = conclude(mail_fields, file_name, mail_request)
            if rating >= 70 and RELAYED < 13:
                RELAYED += 1


def print_statistics():
    statistics = get_statistics()
    table = PrettyTable()
    table.field_names = ["name", "used", "created", "last modified"]
    for record in statistics:
        table.add_row(
            [
                record.name,
                record.counter,
                datetime.fromtimestamp(record.created),
                datetime.fromtimestamp(record.last_modified),
            ]
        )
    print(RELAYED, "emails would be relayed")
    print(table)


def prepare_testing_env():
    Path("./queue").mkdir(parents=True, exist_ok=True)
    Path("./queue/new").mkdir(parents=True, exist_ok=True)
    Path("./undeliverable").mkdir(parents=True, exist_ok=True)
    Path("./attachments").mkdir(parents=True, exist_ok=True)
    settings1 = Settings(username="changeme@changeme", password="changeme")
    push_into_db(settings1)
    utils.import_settings(True, boot_module="testing_boot")


def clean_up():
    try:
        os.remove("testing_salmon.log")
    except FileNotFoundError as e:
        pass
    os.remove("testing_salmon.db")
    shutil.rmtree("./queue", ignore_errors=True)
    shutil.rmtree("./queue/new", ignore_errors=True)
    shutil.rmtree("./undeliverable", ignore_errors=True)
    shutil.rmtree("./attachments", ignore_errors=True)


def main():
    args = parse_arguments()
    if not args.path and args.clean:
        clean_up()
        exit(0)
    elif not args.path and not args.clean:
        eprint("You must specify the path to a directory with eml files!")
        exit(1)
    prepare_testing_env()
    if args.scp:
        use_scp(args)
    else:
        read_from_dir(args)
    print_statistics()
    clean_up()


if __name__ == "__main__":
    main()
