#!/usr/bin/env python3

"""new_email_inotify module.

This module periodically checks if there was an event in queue/new directory thus one or more e-mails came.
Author: Silvie Chlupová
Date    Created: 04/27/2020
"""

import inotify.adapters
import time
from threading import Thread
from apscheduler.scheduler import Scheduler
from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import lockfile
import daemon
import argparse
import os


email_event = 0

def parse_arguments():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--recipient",
        "-r",
        type=str,
        required=True,
        help="error message recipient",
    )
    args = parser.parse_args()
    return args


def send_mail(args):
    text = "Salmon is down, at least 6 hours have passed since the last email."
    sender = "salmon@salmon.info"
    recipient = args.recipient
    server = "127.0.0.1"
    port = 2500

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Salmon error report"
    msg["From"] = sender
    recipients = [recipient]
    msg['To'] = recipient
    part = MIMEText(text, "plain")
    msg.attach(part)

    with SMTP(server, port) as s:
        s.send_message(msg)


def check_dir():
    i = inotify.adapters.Inotify()
    i.add_watch('queue/new')
    global email_event
    while True:
        events = i.event_gen(yield_nones=False, timeout_s=1)
        events = list(events)
        if len(events) > 0:
            email_event += 1


def check_email_event(args):
    global email_event
    if email_event == 0:
        send_mail(args)
    else:
        email_event = 0


def schedule(args):
    sched = Scheduler()
    sched.add_interval_job(lambda: check_email_event(args), hours=6)
    sched.start()


def main(args):
    worker = Thread(target=check_dir)
    worker2 = Thread(target=schedule, args=(args,))
    worker.start()
    worker2.start()


if __name__ == '__main__':
    args = parse_arguments()
    with daemon.DaemonContext(chroot_directory=None, working_directory=os.getcwd()):
        main(args)
