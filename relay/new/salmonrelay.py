"""salmonrelay module.

This module gets an email from the salmonconclude module and saves the eml
and attachment if it is enabled. It sends the eml content to the MQTT topics, if enabled.
Depending on the final rating of the current email and the last checkpoint, it calls the
process_message function, which takes care of sending the email to the recipient. 
If enabled, this module destroys the attachment, links, and reply-to.
Author: Silvie Chlupová
Date    Created: 09/17/2019
"""

import logging
import shutil
import datetime
import sys
import time
import os
import importlib
import iottl
import random
import string
import base64
from re import search as regex_search
from salmon import server
from salmon import utils
from salmon.salmonspam import update_statistics


def get_file_content(filename):
    """Function opens the file and return its content.

    Args:
        filename (str): Name of the file you want to read.
    
    Returns:
        str: Content of the file.
    """
    content = None
    try:
        with open(filename) as f:
            content = f.read()
    except Exception:
        logging.critical("[-] (salmonrelay.py) - Cannot read file %s." % filename)
        pass

    return content


def relay(mail_fields, key, mail_request, final_rating):
    """If the relay is enabled, this function does the relaying.

    First, it destroys the attachment if it is enabled, then it sends the email on
    the MQTT topic, saves the email, and if relaying is enabled,
    it does the last check and the email is sent to the process_message method,
    which takes care of sending the email to the recipient.

    Args:
        mail_fields (dict): Email parsed into a dictionary.
        key (str): Name of the file picked up from queue/new.
        mail_request (MailRequest): Instance of the MailRequest class with eml data.
        final_rating (int): Final email rating.
    """
    queuePath = utils.settings.data["directory"]["queuepath"]
    relay_enabled = utils.settings.data["relay"]["relay_enabled"]

    source = queuePath + "/new/" + key
    destination = utils.settings.data["directory"]["rawspampath"] + "/" + key

    if (
        len(mail_fields["attachmentFile"]) > 0
        and utils.settings.data["relay"]["destroy_attachment"]
    ):
        save_attachment(mail_fields)

    if (
        utils.settings.data["relay"]["mqtt"]
        and mail_fields["text"] != "this is testing email from salmon"
    ):
        useMQTT(source, key)

    if (
        utils.settings.data["relay"]["save_eml"]
        and mail_fields["text"] != "this is testing email from salmon"
    ):
        shutil.copy2(source, destination)

    if relay_enabled:
        relaycounter = utils.settings.data["relay"]["globalcounter"]

        # 12.check - number of relayed emails is limited by time
        if int(server.QueueReceiver.totalRelay) >= relaycounter:
            logging.info("[+] (salmonrelay.py) - Limit reached. No relay.")
        else:
            if final_rating >= 70:
                logging.info("[+] (salmonrelay.py) - Relaying!")
                mail_request = destroy_link(mail_fields, mail_request)
                mail_request = destroy_attachment(mail_fields, mail_request)
                mail_request = destroy_reply_to(mail_fields, mail_request)
                if utils.settings.data["relay"]["save_statistics"]:
                    update_statistics(5)
                processMessage = server.QueueReceiver(queuePath)
                processMessage.process_message(mail_request)
                server.QueueReceiver.totalRelay += 1


def save_attachment(mail_fields):
    """Function saves the attachment into the directory for the attachments.
    
    Args:
        mail_fields (dict): Email parsed into dictionary.
    """
    for i in range(len(mail_fields["attachmentFile"])):
        file_name = (
            str(mail_fields["s_id"]) + "-a-" + str(mail_fields["attachmentFileName"][i])
        )
        logging.info("[+] (salmonrelay.py) - Saving attachment %s." % file_name)
        path = utils.settings.data["directory"]["attachpath"] + "/" + file_name
        with open(path, "wb") as f:
            f.write(mail_fields["attachmentFile"][i])


def useMQTT(file_path, filename):
    """Function prepares the eml message and the global message
    and sends the message to the MQTT using the iottl library.

    Args:
        file_path (str): Full path to the eml file in the queue/new directory.
        filename (str): Name of the file with eml.
    """
    content = get_file_content(file_path)
    stamp = int(time.time())
    eml_msg = {"timestamp": stamp, "filename": filename, "contents": content}

    try:
        ip = regex_search("(?:[0-9]{1,3}\.){3}[0-9]{1,3}", filename)
        if ip is None:
            ip = ""
        else:
            ip = ip.group()

        global_msg = {
            "timestamp": stamp,
            "family": "SMTP",
            "honeypot": utils.settings.data["relay"]["mqtt_honeypot"],
            "source": {"ip": ip},
            "destination": {"ip": utils.settings.data["relay"]["mqtt_destination_ip"]},
            "filename": filename,
        }
    except Exception as e:
        logging.error("[-] (salmonrelay.py) - Error occurred during preparing global message", e)

    try:
        utils.settings.client.send(
            utils.settings.data["relay"]["eml_msg_topic"], eml_msg
        )
    except Exception as e:
        logging.error("[-] (salmonrelay.py) - Error occurred during sending of an eml file", e)

    try:
        utils.settings.client.send(
            utils.settings.data["relay"]["global_msg_topic"], global_msg
        )
    except Exception as e:
        logging.error("[-] (salmonrelay.py) - Error occurred during sending of a global message", e)


def destroy_attachment(mail_fields, mail_request):
    """Function destroys the attachment if the destroy_attachment variable
    is set to True in salmon.yaml.

    Args:
        mail_fields (dict): Email parsed into a dictionary.
        mail_request (MailRequest): Instance of the MailRequest class with eml data.

    Returns:
        MailRequest: changed or unchanged instance of class MailRequest.
    """
    if (
        not mail_fields["attachmentFileName"]
        or not utils.settings.data["relay"]["destroy_attachment"]
    ):
        return mail_request

    for attachment in mail_fields["undecodeAttachmentFile"]:
        l = list(attachment[20 : len(attachment) - 20])
        random.shuffle(l)
        at_part = "".join(l)
        destroyed_attachment = (
            bytes(attachment[:20], encoding="utf-8")
            + bytes(at_part, encoding="utf-8")
            + bytes(attachment[len(attachment) - 20 :], encoding="utf-8")
        )
        logging.debug("[+] (salmonrelay.py) - Destroying attachment!")
        index = mail_request.Data.find(bytes(attachment, encoding="utf-8"))
        if index >= 0:
            before_attachment = mail_request.Data[:index]
            after_attachment = mail_request.Data[index + len(destroyed_attachment) :]
            mail_request.Data = (
                before_attachment + destroyed_attachment + after_attachment
            )
    return mail_request


def destroy_link(mail_fields, mail_request):
    """Function destroys links if the destroy_link variable is set to True in salmon.yaml.

    Args:
        mail_fields(dict): Email parsed into a dictionary.
        mail_request (MailRequest): Instance of the MailRequest class with eml data.
    
    Returns:
        MailRequest: changed or unchanged instance of class MailRequest.
    """
    if not mail_fields["links"] or not utils.settings.data["relay"]["destroy_link"]:
        return mail_request

    for link in mail_fields["links"]:
        letters = string.ascii_lowercase
        last = None
        for i in range(len(link)):
            if link[i] == ".":
                last = i
        if not last:
            continue
        destroyed_link = (
            link[: -(len(link) - last + 1)] + random.choice(letters) + link[last:]
        )
        try:
            found_link = mail_request.Data.decode().find(link)
        except Exception as error:
            logging.error("[-] (salmonrelay.py) - It wasn't possible to destroy the link!")
        else:
            try:
                mail_request.Data = mail_request.Data.replace(
                    bytes(link, "utf-8"), bytes(destroyed_link, "utf-8")
                )
                logging.debug("[+] (salmonrelay.py) - Destroying link %s to %s" % (link, destroyed_link))
            except Exception as error:
                logging.error("[-] (salmonrelay.py) - It wasn't possible to destroy the link!")
    return mail_request


def destroy_reply_to(mail_fields, mail_request):
    """Function destroys reply-to if the destroy_reply_to variable is set to True in salmon.yaml.

    Args:
        mail_fields(dict): Email parsed into a dictionary.
        mail_request (MailRequest): Instance of the MailRequest class with eml data.

    Returns:
        MailRequest: changed or unchanged instance of the MailRequest class.
    """
    if (
        mail_fields["reply-to"] == "-"
        or not utils.settings.data["relay"]["destroy_reply_to"]
    ):
        return mail_request

    reply_to = mail_fields["reply-to"]
    last = None
    for i in range(len(reply_to)):
        if reply_to[i] == ".":
            last = i
    if not last:
        return mail_request
    at_sign = reply_to.find("@")
    destroyed_reply_to = (
        reply_to[: -(len(reply_to) - at_sign - 1)]
        + change_letter(reply_to[at_sign + 1 : last])
        + reply_to[last:]
    )
    logging.debug(
        "[+] (salmonrelay.py) - Destroying reply-to field from %s to %s" % 
        (mail_fields["reply-to"], destroyed_reply_to)
    )
    mail_request["reply-to"] = destroyed_reply_to
    return mail_request


def change_letter(letters):
    """Function changes one in reply-to field.

    Args:
        letters (str): The reply-to field of the email.

    Returns:
        str: Changed reply-to field.
    """
    letters_list = list(letters)
    for i in range(len(letters)):
        new_letter = get_best_letter(letters[i])
        if new_letter:
            letters_list[i] = new_letter
            return "".join(letters_list)
    letters_list[0] = chr(ord(letters_list[0]) + 5)
    return "".join(letters_list)


def get_best_letter(letter):
    """Function returns letter similar to argument letter.

    Args:
        letter (str): The letter we want to change.

    Returns:
        str: Similar letter.or None if there is no similar letter.
    """
    switch = {
        "f": "t",
        "g": "b",
        "h": "k",
        "i": "j",
        "j": "i",
        "J": "I",
        "I": "T",
        "p": "b",
        "b": "p",
        "q": "g",
        "Q": "G",
        "m": "n",
        "n": "m",
        "b": "g",
        "M": "N",
        "I": "J",
        "s": "z",
        "z": "s",
        "T": "I",
        "G": "Q",
        "t": "f",
        "k": "h",
        "P": "B",
        "N": "M",
    }
    return switch.get(letter, None)
