"""salmonmailparser module.

This module takes care of the parsing of the email into the dictionary. 
This dictionary is then passed to the salmonconclude module. 
The dictionary is created from an instance of the MailRequest class. 
If something goes wrong, the eml file is stored in the undeliverable email directory 
with the name specified by the key argument.
Author: Silvie Chlupová
Date    Created: 09/17/2019
"""

import email.message
import email.parser
import logging
import os
import re
import hashlib
import base64
import shutil
import ssdeep
import os
import quopri
from email.header import decode_header
from datetime import datetime
from email.utils import parseaddr
from salmon import salmonrelay
from salmon import server
from salmon import utils
from salmon import salmonconclude
from enum import Enum


class Code(Enum):
    SUCCESS = 1
    ERROR = 2
    UNDELIVERABLE = 3


def process_email(key, mail_request):
    """Function processes the email into a dictionary,
    which is then passed to the salmonconclude module.

    Args:
        key (str): Name of the file being processed.
        mail_request (MailRequest): Instance of the MailRequest class with eml data.

    Returns:
        int: Final email rating when the environmental variable SALMON_SETTINGS_MODULE is set.
    """
    mail_fields = {
        "to": [],
        "reply-to": "",
        "from": "",
        "from_name": "",
        "subject": "",
        "date": "",
        "text": "",
        "html": "",
        "attachmentFileName": [],
        "attachmentFile": [],
        "undecodeAttachmentFile": [],
        "links": [],
        "ssdeep": "",
        "len": "",
        "s_id": "",
    }
    p = email.parser.BytesParser()
    msg = p.parsebytes(mail_request.Data)
    code = None

    if get_recipient(msg, mail_fields) == Code.ERROR:
        code = Code.UNDELIVERABLE
    elif get_sender(msg, mail_fields) == Code.ERROR:
        code = Code.UNDELIVERABLE
    elif get_email_parts(msg, mail_fields) == Code.ERROR:
        code = Code.UNDELIVERABLE

    get_reply_to(msg, mail_fields)
    get_subject(msg, mail_fields)
    get_links(msg, mail_fields)
    mail_fields["date"] = datetime.timestamp(datetime.today())

    if get_ssdeep(msg, mail_fields) == Code.ERROR:
        code = Code.UNDELIVERABLE
    elif get_email_id(msg, mail_fields) == Code.ERROR:
        code = Code.UNDELIVERABLE

    if code == Code.UNDELIVERABLE:
        logging.error("[-] (salmonmailparser.py) - Some issue in parsing file %s" % key)
        move_to_undeliverable(key)
        return None

    if not "SALMON_SETTINGS_MODULE" in os.environ:
        salmonconclude.conclude(mail_fields, key, mail_request)
    return mail_fields


def get_links_list(input_body):
    """Function gets links from the email body.

    Args:
        input_body (str): text/plain or text/html from the email.

    Returns:
        list: List of links from text/plain or text/html.
    """
    link_regex_pattern = re.compile(
        r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)"
        "(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+"
        "|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?\xab\xbb\u201c\u201d\u2018\u2019]))"
    )
    link_list = set([mgroups[0] for mgroups in link_regex_pattern.findall(input_body)])
    link_list = list(set(link_list))
    logging.debug("[+] (salmonmailparser.py) - Found links %s." % ", ".join(link_list))
    return link_list


def get_fuzzy_hash(mail_fields):
    """Function calculates a hash of body_html, body_plain or subject.

    Args:
        mail_fields (dict): Email fields parsed into a dictionary.

    Returns:
        str: Hash calculated from email fields.
    """
    random_text = """In convallis. Fusce aliquam vestibulum ipsum. Proin in tellus sit amet 
    nibh dignissim sagittis. Donec vitae arcu. Class aptent taciti sociosqu ad litora 
    torquent per conubia nostra, per inceptos hymenaeos. Sed elit dui, pellentesque a, 
    faucibus vel, interdum nec, diam."""
    if len(mail_fields["html"]) > 0:
        logging.debug("[+] (salmonmailparser.py) - Calculating the hash from body_html.")
        if len(mail_fields["html"]) < 120:
            data = mail_fields["html"] + " " + mail_fields["subject"] + random_text
        else:
            data = mail_fields["html"] + " " + mail_fields["subject"]
    elif len(mail_fields["text"]) > 0:
        logging.debug("[+] (salmonmailparser.py) - Calculating the hash from body_plain.")
        if len(mail_fields["text"]) < 120:
            data = mail_fields["text"] + " " + mail_fields["subject"] + random_text
        else:
            data = mail_fields["text"] + " " + mail_fields["subject"]
    else:
        logging.debug(
            "[+] (salmonmailparser.py) - Calculating the hash from subject, from and random text."
        )
        data = mail_fields["subject"] + mail_fields["from"] + random_text
    mail_fields["len"] = (
        len(mail_fields["html"]) + len(mail_fields["subject"]) + len(mail_fields["text"])
    )
    return ssdeep.hash(data)


def get_md5(text):
    """Function calculates the md5 hash,
    which is used for the first part of the attachment name.

    Args:
        text (str): Text from body_html, body_plain or subject.

    Returns:
        str: Function returns a hash.
    """
    m = hashlib.md5()
    try:
        m.update(text)
    except TypeError as error:
        text = text.encode("utf-8")
        m.update(text)
    md5_hash = m.hexdigest()
    logging.debug("[+] (salmonmailparser.py) - Calculated the MD5 hash %s." % md5_hash)
    return md5_hash


def move_to_undeliverable(key):
    """Function moves the eml file to the directory for undeliverable emails.

    Args:
        key (str): Name of the file that will be moved.
    """
    queuepath = utils.settings.data["directory"]["queuepath"]
    undeliverable_path = utils.settings.data["directory"]["undeliverable_path"]
    logging.error("[-] (salmonmailparser.py) - Copying %s into undeliverable directory" % key)
    shutil.copyfile(queuepath + "/new/" + key, undeliverable_path + "/" + key)


def process_email_parts_recursively(msg, mail_fields):
    """Function processes parts of the email when the message is multipart.

    Args:
        msg (Message): Instance of the Message class with parts of the email.
        mail_fields (dict): Email fields parsed into a dictionary.
    """
    while isinstance(msg.get_payload(), email.message.Message):
        msg = msg.get_payload()

    if msg.is_multipart():
        for inner_msg in msg.get_payload():
            process_email_parts_recursively(inner_msg, mail_fields)
    else:
        file_name = None
        try:
            fileName, encoding = decode_header(msg.get_filename())[0]
        except TypeError as error:
            pass
        else:
            if encoding == None:
                file_name = fileName
            else:
                file_name = fileName.decode(encoding)

        if msg.get_content_type() == "text/plain" and msg["Content-Disposition"] == None:
            if msg["Content-Transfer-Encoding"] == "base64":
                mail_fields["text"] = base64.b64decode(msg.get_payload()).decode("utf-8")
                logging.debug("[+] (salmonmailparser.py) - text/plain encoded in base64.")
            elif (
                msg["Content-Transfer-Encoding"] == "quoted-printable"
                or msg["Content-Transfer-Encoding"] == "8bit"
            ):
                try:
                    decoded_string = quopri.decodestring(msg.get_payload())
                    mail_fields["text"] = decoded_string.decode("utf-8")
                except UnicodeDecodeError as e:
                    mail_fields["text"] = msg.get_payload()
                logging.debug("[+] (salmonmailparser.py) - text/plain encoded in quoted-printable.")
            elif msg["Content-Transfer-Encoding"] == "binary":
                logging.debug("[+] (salmonmailparser.py) - text/plain encoded in binary.")
                text = msg.get_payload()
                try:
                    mail_fields["text"] = text.decode("utf-8")
                except Exception as e:
                    mail_fields["text"] = text
            else:
                mail_fields["text"] = msg.get_payload()
        elif msg.get_content_type() == "text/html":
            if msg["Content-Transfer-Encoding"] == "base64":
                mail_fields["html"] = base64.b64decode(msg.get_payload()).decode("utf-8")
                logging.debug("[+] (salmonmailparser.py) - text/html encoded in base64.")
            elif (
                msg["Content-Transfer-Encoding"] == "quoted-printable"
                or msg["Content-Transfer-Encoding"] == "8bit"
            ):
                decoded_string = quopri.decodestring(msg.get_payload())
                mail_fields["html"] = decoded_string.decode("utf-8")
                logging.debug("[+] (salmonmailparser.py) - text/html encoded in quoted-printable.")
            elif msg["Content-Transfer-Encoding"] == "binary":
                logging.debug("[+] (salmonmailparser.py) - text/html encoded in binary.")
                html = msg.get_payload()
                try:
                    mail_fields["html"] = html.decode("utf-8")
                except Exception as e:
                    mail_fields["html"] = html
            else:
                mail_fields["html"] = msg.get_payload()
        elif msg["Content-Disposition"] != None and msg["Content-Disposition"].find("inline") >= 0:
            process_attachment(msg, file_name, mail_fields)
        elif (
            msg["Content-Disposition"] != None
            and msg["Content-Disposition"].find("attachment") >= 0
        ):
            process_attachment(msg, file_name, mail_fields)
        elif msg.get_filename() != None:
            process_attachment(msg, file_name, mail_fields)
        else:
            logging.error(
                "[-] (salmonmailparser.py) - No match for text/html content_type or Content-Disposition"
            )
    return None


def process_attachment(msg, file_name, mail_fields):
    """Function processes attachment into dictionary with the email fields.

    Args:
        msg (Message): Instance of the Message class with parts of the email.
        file_name (str): Name of the attachment file parsed from the email.
        mail_fields (dict): Email fields parsed into a dictionary.
    """
    mail_fields["attachmentFile"].append(msg.get_payload(decode=True))
    mail_fields["undecodeAttachmentFile"].append(msg.get_payload())
    mail_fields["attachmentFileName"].append(file_name)
    logging.info("[+] (salmonmailparser.py) - Found attachment.")


def get_recipient(msg, mail_fields):
    """Function gets the email address of the recipient.

    Args:
        msg (Message): Instance of the Message class with parts of the email.
        mail_fields (dict): Email fields parsed into a dictionary.

    Returns:
        int: Error code ERROR if something went wrong, SUCCESS otherwise.
    """
    try:
        if msg["to"] != None:
            to_address_list = msg["to"].split(",")
            for to in to_address_list:
                name, to_field = parseaddr(to.replace("'", ""))
                name, encoding = decode_header(name)[0]
                if encoding != None:
                    name = name.decode(encoding)
                email_name_tuple = (to_field, name)
                mail_fields["to"].append(email_name_tuple)
        else:
            logging.critical("To field has value None")
            return Code.ERROR
        if msg["bcc"] != None:
            bcc_address_list = msg["bcc"].split(",")
            for to in bcc_address_list:
                name, bcc_field = parseaddr(to.replace("'", ""))
                email_name_tuple = (bcc_field, name)
                mail_fields["to"].append(email_name_tuple)
        if len(mail_fields["to"]) == 0:
            logging.error("[-] (salmonmailparser.py) - Email doesn't have any recipient!")
            return Code.ERROR
        recipients = []
        for i in range(len(mail_fields["to"])):
            recipients.append(mail_fields["to"][i][0])
        logging.debug("[+] (salmonmailparser.py) - Email recipients %s." % ", ".join(recipients))
    except Exception as e:
        logging.critical("Some issue in parsing 'to' field.")
        return Code.ERROR
    return Code.SUCCESS


def get_sender(msg, mail_fields):
    """Function gets the email address of the sender.

    Args:
        msg (Message): Instance of the Message class with parts of the email.
        mail_fields (dict): Email fields parsed into a dictionary.

    Returns:
        int: Error code ERROR if something went wrong, SUCCESS otherwise.
    """
    try:
        if msg["from"] != None:
            from_name_field, from_field = parseaddr(msg["from"])
            from_name_field, encoding = decode_header(from_name_field)[0]
            if encoding != None:
                from_name_field = from_name_field.decode(encoding)
            mail_fields["from_name"] = from_name_field
            mail_fields["from"] = from_field
        else:
            logging.error("[-] (salmonmailparser.py) - From field has value None")
            return Code.ERROR
        logging.debug("[+] (salmonmailparser.py) - Email sender %s." % mail_fields["from"])
    except Exception as e:
        logging.error("[-] (salmonmailparser.py) - Some issue in parsing 'from' field.")
        return Code.ERROR
    return Code.SUCCESS


def get_reply_to(msg, mail_fields):
    """Function gets the email address of the reply-to.

    Args:
        msg (Message): Instance of the Message class with parts of the email.
        mail_fields (dict): Email fields parsed into a dictionary.
    """
    valid_email_regex = "^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$"
    try:
        if msg["reply-to"] != None:
            _, reply_to = parseaddr(msg["reply-to"])
            if re.search(valid_email_regex, reply_to):
                mail_fields["reply-to"] = reply_to
            else:
                mail_fields["reply-to"] = "-"
        else:
            mail_fields["reply-to"] = "-"
        logging.debug(
            "[+] (salmonmailparser.py) - Email reply-to field %s." % mail_fields["reply-to"]
        )
    except Exception as e:
        logging.error("[-] (salmonmailparser.py) - Some issue in parsing 'reply-to' field.")


def get_subject(msg, mail_fields):
    """Function gets the email subject.

    Args:
        msg (Message): Instance of the Message class with parts of the email.
        mail_fields (dict): Email fields parsed into a dictionary.
    """
    try:
        subject, encoding = decode_header(msg.get("subject"))[0]
        if encoding == None:
            mail_fields["subject"] = subject
        else:
            mail_fields["subject"] = subject.decode(encoding)
    except Exception as e:
        logging.error("[-] (salmonmailparser.py) - Some issue in parsing 'subject' field.")


def get_email_parts(msg, mail_fields):
    """Function gets the email parts - text/plain, text/html and attachment.

    Args:
        msg (Message): Instance of the Message class with parts of the email.
        mail_fields (dict): Email fields parsed into a dictionary.

    Returns:
        int: Error code ERROR if something went wrong, SUCCESS otherwise.
    """
    try:
        process_email_parts_recursively(msg, mail_fields)
    except Exception as e:
        logging.error(
            "[-] (salmonmailparser.py) - Some issue in process_email_parts_recursively function"
        )
        return Code.ERROR
    return Code.SUCCESS


def get_links(msg, mail_fields):
    """Function gets links from the email.

    Args:
        msg (Message): Instance of the Message class with parts of the email.
        mail_fields (dict): Email fields parsed into a dictionary.
    """
    try:
        mail_fields["links"] = get_links_list(mail_fields["html"])
        mail_fields["links"].extend(get_links_list(mail_fields["text"]))
    except Exception as e:
        logging.error("[-] (salmonmailparser.py) - Some issue in parsing 'links' field.")


def get_ssdeep(msg, mail_fields):
    """Function adds a hash computed from parts of the email to the mail_fields dictionary.

    Args:
        msg (Message): Instance of the Message class with parts of the email.
        mail_fields (dict): Email fields parsed into a dictionary.

    Returns:
        int: Error code ERROR if something went wrong, SUCCESS otherwise.
    """
    try:
        mail_fields["ssdeep"] = get_fuzzy_hash(mail_fields)
    except Exception as e:
        logging.error(
            "[-] (salmonmailparser.py) - Error occured while calculating fuzzy hash for spam id"
        )
        return Code.ERROR
    return Code.SUCCESS


def get_email_id(msg, mail_fields):
    """Function adds a hash computed from parts of the email to the mail_fields dictionary.

    Args:
        msg (Message): Instance of the Message class with parts of the email.
        mail_fields (dict): Email fields parsed into a dictionary.

    Returns:
        int: Error code ERROR if something went wrong, SUCCESS otherwise.
    """
    try:
        if mail_fields["html"]:
            mail_fields["s_id"] = get_md5(mail_fields["subject"] + mail_fields["html"])
        elif mail_fields["text"]:
            mail_fields["s_id"] = get_md5(mail_fields["subject"] + mail_fields["text"])
        else:
            mail_fields["s_id"] = get_md5(mail_fields["subject"])
    except Exception as e:
        if len(mail_fields["attachmentFile"]) > 0:
            logging.error("[-] (salmonmailparser.py) - Error occured while calculating email id")
            return Code.ERROR
        return Code.SUCCESS
    return Code.SUCCESS
