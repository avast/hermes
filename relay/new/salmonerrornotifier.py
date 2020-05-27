#!/usr/bin/env python3

"""salmonerrornotifier module.

This module checks if receiver and relay are running.
Author: Silvie Chlupová
Date    Created: 04/26/2020
"""

from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import psutil
import socket
import yaml
import os


def get_salmon_config():
    """Function reads salmon.yaml and returns its content."""
    confpath = os.path.dirname(os.path.realpath(__file__)) + "/salmon.yaml"
    with open(confpath) as f:
        data = yaml.safe_load(f)
    return data


def send_email(salmon_receiver, salmon_relay, data):
    """Function prepares and sends an email with an error message.

    Args:
        salmon_receiver (bool): False if receiver is down, True otherwise.
        salmon_relay (bool): False if relay is down, True otherwise.
    """
    text = "This is an error message sent from salmon honeypot. "
    if not salmon_receiver:
        text += "Salmon receiver is not running! "
    if not salmon_relay:
        text += "Salmon relay is not running! "

    if not salmon_receiver or not salmon_relay:
        sender = data["global"]["error_msg_sender"]
        recipient = data["global"]["error_msg_receiver"]
        server = data["relay"]["relayhost"]
        port = data["relay"]["relayport"]

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Salmon error report"
        msg["From"] = sender
        recipients = [recipient]
        msg["To"] = recipient
        part = MIMEText(text, "plain")
        msg.attach(part)

        with SMTP(server, port) as s:
            s.send_message(msg)


def check_salmon(data):
    """Function check if the salmon receiver process exists and if
    the salmon relay is not down.

    Args:
        data (dict): Data from salmon.yaml
    """
    salmon_receiver = True
    salmon_relay = True
    if not "salmon" in (p.name() for p in psutil.process_iter()):
        salmon_receiver = False
    server = data["receiver"]["listenhost"]
    port = data["receiver"]["listenport"]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = s.connect_ex((server, port))
    if result != 0:
        salmon_relay = False
    s.close()
    send_email(salmon_receiver, salmon_relay, data)


if __name__ == "__main__":
    data = get_salmon_config()
    check_salmon(data)
