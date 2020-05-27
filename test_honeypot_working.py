"""
This tests that honeypot is working so it can send an e-mail using running salmon and then check your inbox.
Author: Silvie Chlupová
Date    Created: 04/26/2020
"""

import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
import argparse
import time
import imaplib
import email
import os


def parse_arguments():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--listenhost", type=str, required=True, help="Where is salmon receiver running"
    )
    parser.add_argument(
        "--listenport", type=int, required=True, help="Port where is salmon receiver listening"
    )
    parser.add_argument(
        "--recipient", type=str, required=True, help="Recipient email address"
    )
    parser.add_argument(
        "--password", "-p", type=str, required=True, help="Password for your inbox, "\
            "please note that if you use gmail you have to set the app specific password, "\
                "not that one you use usually!"
    )
    parser.add_argument(
        "--imap",
        type=str,
        default="imap.seznam.cz",
        help="Set the IMAP server, this depends on the `recipient` argument, "\
            "by default seznam.cz IMAP server for seznam email address",
    )
    parser.add_argument(
        "--sender", type=str, default="no-reply@salmon.com", help="Sender email address"
    )
    parser.add_argument(
        "--text",
        "-t",
        type=str,
        default="this is testing email from salmon",
        help="You can set your own text of the testing email "\
            "in case you think that this email would be relayed!"
    )
    args = parser.parse_args()
    return args


def send_mail(send_from, send_to, text, server, port):
    subject = "testing email from salmon"
    msg = MIMEMultipart()
    msg["From"] = send_from
    msg["To"] = send_to
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = subject
    msg.attach(MIMEText(text, "plain", "utf-8"))

    with smtplib.SMTP(server, port) as server:
        server.sendmail(send_from, send_to, msg.as_string())


def search(key, value, con):  
    result, data = con.search(None, key, '"{}"'.format(value)) 
    return data 
  

def get_emails(result_bytes, con): 
    msg = []
    for num in result_bytes[0].split(): 
        typ, data = con.fetch(num, '(RFC822)')
        email_message = email.message_from_bytes(data[0][1])
        msg.append(email_message['Date']) 
    return msg


def check_inbox(args, con, box):
    con.select(box)
    msg = get_emails(search('FROM', '{}'.format(args.sender), con), con)
    return msg


def main():
    args = parse_arguments()
    if args.recipient.split('@')[1] != "seznam.cz" and args.imap == "imap.seznam.cz":
        raise Exception("Specify IMAP server!")
    send_mail(
        args.sender, args.recipient, args.text, args.listenhost, args.listenport
    )
    print("Let's wait 10 seconds")
    time.sleep(10)
    con = imaplib.IMAP4_SSL(args.imap)
    con.login(args.recipient, args.password)
    msg = check_inbox(args, con, 'Inbox')
    if not msg:
        if args.imap == "imap.gmail.com":
            msg = check_inbox(args, con, '"[Gmail]/Spam"')
        else:
            msg = check_inbox(args, con, 'Spam')
    error_msg = "I'm sorry, the email is not there, "\
        "please check the salmon.log if it was relayed or wait a little bit longer."
    if not msg:
        print(error_msg)
    else:
        print("These are dates of messages from this honeypot")
        for m in msg:
            print(m)


if __name__ == "__main__":
    main()
