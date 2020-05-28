"""salmonconclude module.

This module calculates the final email rating using the functions in this module
and the Spam class from the salmonspam module. First, it creates instance of 
the Spam class from thr email fields that are prepared as a dictionary from the salmonmailparser module. 
Then it creates an instance of the MailFields class that represents a
table with email fields in the database, instance of the Sender class that represents
a table with the sender informations and list of instances of the Recipient class 
that represents a table with the recipient informations. Using Spam class methods,
the final email rating is calculated and passed to the salmonrelay module.
Author: Silvie Chlupová
Date    Created: 09/17/2019
"""

import logging
import ssdeep
import warnings
warnings.filterwarnings("ignore")
import re
import os
from datetime import datetime
from salmon import salmonrelay
from salmon import utils
from salmon.salmondb import MailFields
from salmon.salmondb import MaybeTestMail
from salmon.salmondb import TestMail
from salmon.salmondb import Sender
from salmon.salmondb import Link
from salmon.salmondb import push_into_db
from salmon.salmondb import get_usernames
from salmon.salmondb import get_links
from salmon.salmondb import push_email_into_db
from salmon.salmondb import get_link_by_name
from salmon.salmondb import get_testmail_by_mailfield_id
from salmon.salmondb import get_mail_fields_by_id
from salmon.salmondb import get_maybetestmail_by_mailfield_id
from salmon.salmondb import delete_maybetestmail_record
from salmon.salmondb import update_link_rating
from salmon.salmondb import email_into_db
from salmon.salmondb import move_to_testmail
from salmon.salmonspam import Spam
from salmon.salmonspam import update_statistics


def conclude(mail_fields, key, mail_request):
    """This is a key function of the whole relay part.

    Function calls other auxiliary functions and calculates the
    final rating of the email. This is called each time a new email arrives.

    Args:
        mail_fields (dict): Email parsed in the dictionary.
        key (str): Name of the file picked up from queue/new.
        mail_request (MailRequest): Instance of the MailRequest class with eml data.

    Returns:
        int: Final email rating when the environmental variable SALMON_SETTINGS_MODULE is set.
    """
    logging.debug(
        "[+] (salmonconclude.py) - In conclude, started calculating the final spam rating."
    )
    attachment = False
    if mail_fields["attachmentFileName"]:
        attachment = True

    # just for the testing purpose
    if mail_fields["text"] == "this is testing email from salmon":
        salmonrelay.relay(mail_fields, key, mail_request, 100)
        return 100

    spam = Spam(
        subject=str(mail_fields["subject"]),
        email_date=str(mail_fields["date"]),
        body_plain=mail_fields["text"],
        body_html=mail_fields["html"],
        ssdeep=mail_fields["ssdeep"],
        length=mail_fields["len"],
        attachment=attachment,
    )
    database_mail_fields = MailFields(
        subject=spam.subject,
        email_date=spam.email_date,
        body_plain=spam.body_plain,
        body_html=spam.body_html,
        ssdeep=spam.ssdeep,
        length=spam.length,
        attachment=spam.attachment,
    )
    sender = Sender(mail_fields["from"], mail_fields["from_name"], database_mail_fields)
    recipient_model_list = spam.get_recipients_for_db(
        mail_fields["to"], database_mail_fields
    )

    # 1.check - try to find password in email
    spam.find_password_in_email()

    # 2.check - try to find username in email
    usernames = get_usernames()
    spam.find_username_in_email(usernames)

    # 3.check - check if the email contains links
    links_from_db = None
    links_into_db = None
    if len(mail_fields["links"]) > 0:
        links_from_db = get_links()
        links_into_db = spam.get_links_for_db(mail_fields["links"], links_from_db)

    # 4.check - verify that the email contains an attachment
    if len(mail_fields["attachmentFileName"]) > 0:
        spam.rating -= 10
        if utils.settings.data["relay"]["save_statistics"]:
            update_statistics(1)

    # 5.check - try to find the word test or testing in the email
    spam.find_word_test_in_email()

    # 6.check - verify that the recipient has already been used in test emails
    is_recipient_in_testmail = spam.is_recipient_in_testmail(mail_fields["to"])

    # 7.check - check the time the email arrived
    spam.investigate_time()

    # 8.check - try to find the IP address of the honeypot in the email
    spam.find_ip_address_in_email()

    # 9.check - analyze what is written in the email
    # this is optional and has to be set in the salmon.yaml
    if utils.settings.data["relay"]["analyze_text"]:
        analyze_text(mail_fields, spam)

    # 10.check - verify that similar email is not already in the database
    tables = get_tables_from_similar(spam)

    # there is a very high probability that email is testing
    push_into_db_testing(
        tables, spam, database_mail_fields, recipient_model_list, sender
    )

    # Verify that current email doesn't look more like a testing one
    can_push_into_db = False
    if len(tables) > 0:
        updater = DBUpdater(spam.rating, mail_fields, usernames)
        for table in tables:
            if isinstance(table, MaybeTestMail):
                if updater(table):
                    can_push_into_db = True

    # there is a chance that email is testing but not for sure
    push_into_db_maybetesting(
        tables,
        spam,
        can_push_into_db,
        database_mail_fields,
        recipient_model_list,
        sender,
    )

    # similar is in the maybe_test_emails table, but this one has a high rating
    for table in tables:
        if isinstance(table, MaybeTestMail) and (
            spam.rating >= 70 or is_recipient_in_testmail
        ):
            logging.info(
                "[+] (salmonconclude.py) - Moving a record from the maybe_test_emails table to the test_emails table."
            )
            move_to_testmail(table.mail_fields_id)

    if is_recipient_in_testmail:
        recipient_in_testmail(spam)

    if len(mail_fields["links"]) > 0:
        spam.update_link_rating(mail_fields["links"], links_from_db)

    if links_into_db and spam.rating >= 50:
        for link in links_into_db:
            link_model = Link(link, 1, spam.rating)
            push_into_db(link_model)

    # 11.check - match the email against the rule file
    # this is optional and has to be set in the salmon.yaml
    if utils.settings.data["relay"]["use_rule_file"]:
        for rule in utils.settings.rules:
            if spam.match_against_rule_file(rule):
                logging.info(
                    "[+] (salmonconclude.py) - Email successfully matched against the rule %s"
                    % rule["name"]
                )
                spam.rating = 100

    final_rating = spam.rating

    del spam
    if "SALMON_SETTINGS_MODULE" in os.environ:
        return final_rating
    salmonrelay.relay(mail_fields, key, mail_request, final_rating)


def recipient_in_testmail(spam):
    """Function writes information about the email recipient to the log file.

    Args:
        spam (Spam): Instance of the Spam class.
    """
    logging.info(
        "[+] (salmonconclude.py) - The recipient was used in a 100% test email, so this is a test email."
    )
    if utils.settings.data["relay"]["save_statistics"]:
        update_statistics(2)
    if spam.rating < 70:
        # although the email does not look like a test email, it should be relayed
        spam.rating = 100


def push_into_db_maybetesting(records, spam, can_push, mail_fields, recipient, sender):
    """Function pushes an email with a rating between 50 and 70 into the database.

    Args:
        records (list): List of similar records.
        spam (Spam): Instance of the Spam class.
        can_push (bool): Decide if the email can be pushed into the database.
        mail_fields (MailFields): Database model of parsed email fields.
        recipient (Recipient): List of instances of the Recipient class.
        sender (Sender): Instance of the Sender class.
    """
    for record in records:
        if (spam.rating < 70 and spam.rating >= 50) or isinstance(record, MaybeTestMail):
            if not isinstance(record, MaybeTestMail) or can_push:
                email_into_db(spam.rating, mail_fields, recipient, sender)
            if spam.rating < 50:
                # similar is already in the maybe_test_emails table
                spam.rating = 50
                logging.info(
                    "[+] (salmonconclude.py) - Similar email is already in the maybe_test_emails table."
                )
                if utils.settings.data["relay"]["save_statistics"]:
                    update_statistics(3)
    if len(records) == 0 and (spam.rating < 70 and spam.rating >= 50):
        email_into_db(spam.rating, mail_fields, recipient, sender)


def analyze_text(mail_fields, spam):
    """Function analyzes the text in body_plain and body_html using
    the methods from the Spam class.

    Args:
        mail_fields (dict): Email parsed in the dictionary.
        spam (Spam): Instance of the Spam class.
    """
    url_regex_pattern = re.compile(
        r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)"
        "(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+"
        "|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?\xab\xbb\u201c\u201d\u2018\u2019]))"
    )
    if mail_fields["text"]:
        spam.analyze_text_in_body(
            utils.settings.nlp, "plain", url_regex_pattern, mail_fields
        )
    elif mail_fields["html"]:
        spam.analyze_text_in_body(
            utils.settings.nlp, "html", url_regex_pattern, mail_fields
        )


def push_into_db_testing(records, spam, mail_fields, recipient, sender):
    """Function pushes email with a rating over 70 into the database.

    Args:
        records (list): List of similar records.
        spam (Spam): Instance of the Spam class.
        mail_fields (MailFields): Database model of parsed email fields.
        recipient (Recipient): List of instances of the Recipient class.
        sender (Sender): Instance of the Sender class.
    """
    for record in records:
        if spam.rating >= 70 or isinstance(record, TestMail):
            if not isinstance(record, TestMail):
                test_email = TestMail(mail_fields)
                push_email_into_db(mail_fields, test_email, recipient, sender)
            if spam.rating < 70:
                # similar is already in the test_emails table
                spam.rating = 100
                logging.info(
                    "[+] (salmonconclude.py) - Similar email is already in the test_emails table."
                )
                if utils.settings.data["relay"]["save_statistics"]:
                    update_statistics(4)
    if len(records) == 0 and spam.rating >= 70:
        test_email = TestMail(mail_fields)
        push_email_into_db(mail_fields, test_email, recipient, sender)


def get_tables_from_similar(spam):
    """Check if similar emails are in the database.

    Args:
        spam (Spam): Instance of the Spam class.
    
    Returns:
        list: List of similar records.
    """
    similar_emails_ids = spam.get_ids_for_similarity_check()
    records = []
    if similar_emails_ids:
        for spam_id in similar_emails_ids:
            if utils.settings.data["relay"]["analyze_text"]:
                records_list = spam.get_records_if_similar(spam_id, utils.settings.nlp)
                records.append(records_list)
            else:
                mail_fields_from_db = get_mail_fields_by_id(spam_id)
                record = get_testmail_by_mailfield_id(mail_fields_from_db.id)
                if record:
                    records.append(record)
                record = get_maybetestmail_by_mailfield_id(mail_fields_from_db.id)
                if record:
                    records.append(record)
        try:
            records = [item for sublist in records for item in sublist]
        except TypeError as e:
            pass
        if len(records) > 0:
            logging.debug(
                "[+] (salmonconclude.py) - There are similar emails in the database."
            )
    return records


class DBUpdater:
    """The class decides if the current email doesn't look more like  a testing one.

    Attributes:
        rating (int): Current email rating.
        mail_fields (dict): Email parsed in the dictionary.
        usernames (list): List of the honeypot usernames.
    """

    __slots__ = ("rating", "mail_fields_dict", "usernames_from_db", "__internal_rating")

    def __init__(self, rating, mail_fields, usernames, __internal_rating=0):
        self.rating = rating
        self.mail_fields_dict = mail_fields
        self.usernames_from_db = usernames
        self.__internal_rating = __internal_rating

    def __call__(self, table):
        if self.rating > table.rating:
            self.__internal_rating += 17
            logging.debug(
                "[+] (salmonconclude.py) - updating internal rating to %d."
                % self.__internal_rating
            )
        mail_fields_from_db = get_mail_fields_by_id(table.mail_fields_id)
        if (
            not self.mail_fields_dict["attachmentFile"]
            and mail_fields_from_db.attachment
        ):
            self.__internal_rating += 17
            logging.debug(
                "[+] (salmonconclude.py) - updating internal rating to %d."
                % self.__internal_rating
            )
        self.resolve_username(mail_fields_from_db)
        if self.mail_fields_dict["links"]:
            self.resolve_links(self.mail_fields_dict["links"])
        if self.__internal_rating >= 60:
            delete_maybetestmail_record(mail_fields_from_db.id)
            return True
        return False

    def resolve_username(self, mail_fields_from_db):
        """Method updates the internal rating based on the subject,
        body_plain and body_html.

        Args:
            mail_fields_from_db (MailFields): Database model of parsed email fields.
        """
        for username in self.usernames_from_db:
            if (
                username in self.mail_fields_dict["subject"]
                and username not in mail_fields_from_db.subject
            ):
                self.__internal_rating += 17
                logging.debug(
                    "[+] (salmonconclude.py) - updating internal rating to %d."
                    % self.__internal_rating
                )
            if (
                username in self.mail_fields_dict["text"]
                and username not in mail_fields_from_db.body_plain
            ):
                self.__internal_rating += 17
                logging.debug(
                    "[+] (salmonconclude.py) - updating internal rating to %d."
                    % self.__internal_rating
                )
            if (
                username in self.mail_fields_dict["html"]
                and username not in mail_fields_from_db.body_html
            ):
                self.__internal_rating += 17
                logging.debug(
                    "[+] (salmonconclude.py) - updating internal rating to %d."
                    % self.__internal_rating
                )

    def resolve_links(self, links):
        """Method updates the internal rating if the current 
        email contains the links that were seen in the test email.

        Args:
            links (list): List of links in the current email.
        """
        for link in links:
            l = get_link_by_name(link)
            if l.rating >= 70:
                self.__internal_rating += 15
                logging.debug(
                    "[+] (salmonconclude.py) - updating internal rating to %d."
                    % self.__internal_rating
                )
