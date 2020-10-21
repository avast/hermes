"""salmonspam module.

This module contains the Spam class which is instantiated from the salmonconclude module.
This class holds the information about email rating. Methods in this class
can change email rating based on checkpoints in salmonconclude.
Author: Silvie Chlupová
Date    Created: 04/26/2020
"""

import logging
import ssdeep
import spacy
import warnings
warnings.filterwarnings("ignore")
import re
import os
import collections
from datetime import datetime
from salmon import utils
from salmon.salmondb import Recipient
from salmon.salmondb import Statistics
from salmon.salmondb import push_into_db
from salmon.salmondb import get_link_by_name
from salmon.salmondb import get_testmail_by_mailfield_id
from salmon.salmondb import get_mail_fields_by_id
from salmon.salmondb import get_maybetestmail_by_mailfield_id
from salmon.salmondb import get_statistics_by_checkpoint_id
from salmon.salmondb import update_link_rating
from salmon.salmondb import get_passwords
from salmon.salmondb import update_statistics_counter
from salmon.salmondb import update_link_counter
from salmon.salmondb import get_recipient_by_email
from salmon.salmondb import get_mail_fields


class Spam:
    """This class holds the information about email rating
    and can change the spam rating.

    Attributes:
        email_date (float): Time when spam arrived.
        ssdeep (str): Hash of spam.
        length (int): Length of spam.
        attachment (bool): If spam has attachment.
        body_plain (str): Text from spam text/plain.
        body_html (str): Text from body text/html.
        subject (str): Text from spam subject.
        rating (int): Spam rating.
    """

    __slots__ = (
        "email_date",
        "ssdeep",
        "length",
        "attachment",
        "body_plain",
        "body_html",
        "subject",
        "rating",
    )

    def __init__(
        self,
        email_date,
        ssdeep,
        length,
        attachment,
        body_plain=None,
        body_html=None,
        subject=None,
        rating=0,
    ):
        self.email_date = email_date
        self.ssdeep = ssdeep
        self.length = length
        self.attachment = attachment
        self.body_plain = body_plain
        self.body_html = body_html
        self.subject = subject
        self.rating = rating

    def __del__(self):
        if self.rating > 100:
            self.rating = 100
        elif self.rating < 0:
            self.rating = 0
        logging.info("[+] (salmonspam.py) - Spam final rating is %d" % self.rating)

    def is_username_in_subject(self, usernames):
        for username in usernames:
            if username in self.subject:
                return True
        return False

    def is_password_in_body_html(self, passwords):
        for password in passwords:
            if password in self.body_html:
                return True
        return False

    def is_username_in_body_html(self, usernames):
        for username in usernames:
            if username in self.body_html:
                return True
        return False

    def get_records_if_similar(self, spam_id, nlp):
        mail_fields_from_db = get_mail_fields_by_id(spam_id)
        similar = 0
        mail_list = []
        if len(mail_fields_from_db.body_plain) > 0 and len(self.body_plain) > 0:
            tokens_db = nlp(mail_fields_from_db.body_plain)
            tokens = nlp(self.body_plain)
            if tokens.similarity(tokens_db) > 0.75:
                logging.info(
                    "[+] (salmonspam.py) - Email with a similar body_plain already in the database."
                )
                similar += 1
        if len(mail_fields_from_db.body_html) > 0 and len(self.body_html) > 0:
            tokens_db = nlp(mail_fields_from_db.body_html)
            tokens = nlp(self.body_html)
            if tokens.similarity(tokens_db) > 0.75:
                logging.info(
                    "[+] (salmonspam.py) - Email with a similar body_html already in the database."
                )
                similar += 1
        if len(mail_fields_from_db.subject) > 0 and len(self.subject) > 0:
            tokens_db = nlp(mail_fields_from_db.subject)
            tokens = nlp(self.subject)
            if tokens.similarity(tokens_db) > 0.75:
                logging.info(
                    "[+] (salmonspam.py) - Email with a similar subject already in the database."
                )
                similar += 1
        if similar >= 1:
            # at least one from [body_plain, body_html, subject] should be similar
            test_mail = get_testmail_by_mailfield_id(mail_fields_from_db.id)
            if test_mail:
                mail_list.append(test_mail)
            maybe_test_mail = get_maybetestmail_by_mailfield_id(mail_fields_from_db.id)
            if maybe_test_mail:
                mail_list.append(maybe_test_mail)
        return mail_list

    def get_field(self, mail_field):
        if mail_field == "body_plain":
            return self.body_plain
        elif mail_field == "body_html":
            return self.body_html
        elif mail_field == "subject":
            return self.subject

    def match_against_rule_file(self, rule):
        if "field" in rule and "pattern" in rule:
            try:
                if rule["field"] == "attachment":
                    if rule["pattern"] and self.attachment:
                        return True
                    elif not rule["pattern"] and not self.attachment:
                        return True
                    else:
                        return False
                field = (
                    re.search(rule["pattern"], self.get_field(rule["field"]))
                    is not None
                )
                return field
            except KeyError:
                logging.debug("Failed to get field %s from case" % rule["field"])
                return None
        elif "AND" in rule:
            out = None
            for r in rule["AND"]:
                r_out = self.match_against_rule_file(r)
                out = r_out if out is None else out and r_out
                if not out:
                    break
            return out
        elif "OR" in rule:
            for r in rule["OR"]:
                if self.match_against_rule_file(r):
                    return True
            return False
        else:
            logging.error("Rule %s not formatted correctly" % str(rule))

    def get_ids_for_similarity_check(self):
        mail_fields_from_db = get_mail_fields()
        ids_for_similarity_check = []
        for mail_fields in mail_fields_from_db:
            ratio = ssdeep.compare(self.ssdeep, mail_fields.ssdeep)
            if ratio >= 50:
                ids_for_similarity_check.append(mail_fields.id)
        return ids_for_similarity_check

    def find_password_in_email(self):
        passwords = get_passwords()
        if self.is_password_in_body_plain(passwords):
            logging.info(
                "[+] (salmonspam.py) - Password found in body_plain: %s..."
                % self.body_plain[:50]
            )
            self.rating = 100
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(6)
        elif self.is_password_in_subject(passwords):
            logging.info(
                "[+] (salmonspam.py) - Password found in subject: %s..."
                % self.subject[:50]
            )
            self.rating = 99
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(7)
        elif self.is_password_in_body_html(passwords):
            logging.info(
                "[+] (salmonspam.py) - Password found in body_html: %s..."
                % self.body_html[:50]
            )
            self.rating = 98
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(8)

    def find_username_in_email(self, usernames):
        if self.is_username_in_body_plain(usernames):
            self.update_rating_username_in_body_plain()
        elif self.is_username_in_subject(usernames):
            self.update_rating_username_in_subject()
        elif self.is_username_in_body_html(usernames):
            self.update_rating_username_in_body_html()

    def find_word_test_in_email(self):
        if "test" in self.body_plain or "testing" in self.body_plain:
            logging.info(
                "[+] (salmonspam.py) - test/testing found in body_plain: %s..."
                % self.body_plain[:50]
            )
            self.rating += 5
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(9)
        elif "test" in self.subject or "testing" in self.subject:
            logging.info(
                "[+] (salmonspam.py) - test/testing found in subject: %s..."
                % self.subject[:50]
            )
            self.rating += 10
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(10)
        elif "test" in self.body_html or "testing" in self.body_html:
            logging.info(
                "[+] (salmonspam.py) - test/testing found in body_html: %s..."
                % self.body_html[:50]
            )
            self.rating += 5
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(11)

    def get_links_for_db(self, links, links_from_db):
        update_rating = True
        links_into_db = []
        l2 = []
        for l1 in links_from_db:
            l2.append(l1.link)
        for link in links:
            if link not in l2:
                links_into_db.append(link)
        for link in links:
            row = get_link_by_name(link)
            try:
                update_link_counter(row)
            except AttributeError as error:
                pass
            else:
                if row.counter >= 3 or row.rating >= 70 or self.white_list(link):
                    update_rating = False
        if update_rating:
            self.rating -= 10
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(12)
        return links_into_db

    def is_password_in_body_plain(self, passwords):
        for password in passwords:
            if password in self.body_plain:
                return True
        return False

    def is_username_in_body_plain(self, usernames):
        for username in usernames:
            if username in self.body_plain:
                return True
        return False

    def is_password_in_subject(self, passwords):
        for password in passwords:
            if password in self.subject:
                return True
        return False

    def update_rating_username_in_body_html(self):
        if self.rating == 98:
            logging.info(
                "[+] (salmonspam.py) - Username and password found in body_html: %s..."
                % self.body_html[:50]
            )
        else:
            logging.info(
                "[+] (salmonspam.py) - Username found in body_html: %s..."
                % self.body_html[:50]
            )
            self.rating += 50
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(13)

    def update_rating_username_in_subject(self):
        if self.rating == 99:
            logging.info(
                "[+] (salmonspam.py) - Username and password found in subject: %s"
                % self.subject
            )
        elif (
            len(self.body_plain) > 500 or len(self.body_html) > 500
        ) and self.rating < 98:
            # there is no password in the email and body_plain or body_html is quite long
            logging.info(
                "[+] (salmonspam.py) - Username found in subject: %s" % self.subject
            )
            self.rating += 30
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(14)
        elif self.rating < 98:
            logging.info(
                "[+] (salmonspam.py) - Username found in subject: %s" % self.subject
            )
            self.rating += 50
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(14)

    def update_rating_username_in_body_plain(self):
        if self.rating == 100:
            logging.info(
                "[+] (salmonspam.py) - Username and password found in body_plain: %s..."
                % self.body_plain[:50]
            )
        elif len(self.body_plain) > 500 and self.rating < 98:
            # there is no password in the email and body_plain is quite long
            logging.info(
                "[+] (salmonspam.py) - Username found in body_plain: %s..."
                % self.body_plain[:50]
            )
            self.rating += 30
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(15)
        elif self.rating < 98:
            logging.info(
                "[+] (salmonspam.py) - Username found in body_plain: %s..."
                % self.body_plain[:50]
            )
            self.rating += 50
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(15)
        elif not self.subject and self.rating < 98:
            # there is no password in the email and subject is missing
            # this still might be the testing one, but testing emails usually have subject
            logging.info(
                "[+] (salmonspam.py) - Username found in body_plain: %s... and subject is missing"
                % self.body_plain[:40]
            )
            self.rating += 40
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(16)

    def get_recipients_for_db(self, to_field, database_mail_fields):
        recipients_for_db = []
        for to in to_field:
            recipient_model = Recipient(to[0], to[1], database_mail_fields)
            recipients_for_db.append(recipient_model)
        return recipients_for_db

    def update_link_rating(self, links, links_from_db):
        for l_db in links_from_db:
            for link in links:
                if link == l_db.link and self.rating > l_db.rating:
                    if self.rating > 100:
                        self.rating = 100
                    row = get_link_by_name(link)
                    try:
                        update_link_rating(row, self.rating)
                    except AttributeError as error:
                        logging.error(
                            "[-] (salmonspam.py) - It wasn't possible to update rating of link %s"
                            % link
                        )

    def is_recipient_in_testmail(self, to_field):
        for to in to_field:
            recipient = get_recipient_by_email(to[0])
            try:
                mail_fields_id = recipient.mail_fields_id
            except AttributeError as error:
                return False
            else:
                if get_testmail_by_mailfield_id(mail_fields_id):
                    logging.info(
                        "[+] (salmonspam.py) - Recipient %s was used in a test mail."
                        % to[0]
                    )
                    return True
        return False

    def investigate_time(self):
        dt_object = datetime.fromtimestamp(float(self.email_date))
        if dt_object.hour >= 12 and dt_object.hour <= 18:
            # test emails are sent during these hours
            self.rating += 5
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(17)

    def find_ip_address_in_email(self):
        honeypot_ip_address = str(utils.settings.data["receiver"]["listenhost"])
        if honeypot_ip_address in self.body_plain:
            logging.info(
                "[+] (salmonspam.py) - Honeypot IP address %s found in body_plain: %s..."
                % (honeypot_ip_address, self.body_plain[:50])
            )
            self.rating += 70
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(18)
        elif honeypot_ip_address in self.subject:
            logging.info(
                "[+] (salmonspam.py) - Honeypot IP address %s found in subject: %s..."
                % (honeypot_ip_address, self.subject[:50])
            )
            self.rating += 70
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(19)
        elif honeypot_ip_address in self.body_html:
            logging.info(
                "[+] (salmonspam.py) - Honeypot IP address %s found in body_html: %s..."
                % (honeypot_ip_address, self.body_html[:50])
            )
            self.rating += 70
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(20)

    def analyze_text_in_body(self, nlp, text, url_regex_pattern, mail_fields):
        if text == "plain":
            text = re.sub(url_regex_pattern, "", self.body_plain)
        else:
            text = re.sub(url_regex_pattern, "", self.body_html)
        tokens = nlp(text)
        real_world_words = []
        for token in tokens:
            if len(str(token)) > 2 and (
                token.pos_ == "NOUN" or token.pos_ == "PROPN" or token.pos_ == "VERB"
            ):
                real_world_words.append(token)
        if len(real_world_words) >= 10:
            # it's very unlikely that testing emails can contain so many real-world words
            self.rating -= 15
            logging.info(
                "[+] (salmonspam.py) - This email contains too many real-world words."
            )
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(21)
        elif (
            len(real_world_words) < 3
            and len(mail_fields["links"]) == 0
            and len(mail_fields["attachmentFileName"]) == 0
        ):
            self.rating += 10
            logging.info(
                "[+] (salmonspam.py) - This email contains few real-world words."
            )
            if utils.settings.data["relay"]["save_statistics"]:
                update_statistics(22)
        self.analyze_email_main_topic(tokens)

    def analyze_email_main_topic(self, tokens):
        email_labels = {}
        email_favorite_topics = {}
        for ent in tokens.ents:
            if ent.label_ not in ["PERCENT", "CARDINAL", "DATE"]:
                if ent.label_ not in email_labels.keys():
                    email_labels[ent.label_] = 1
                    email_favorite_topics[ent.label_] = [ent.text.strip()]
                else:
                    email_labels[ent.label_] += 1
                    email_favorite_topics[ent.label_].append(ent.text.strip())
        most_common_label = 0
        for key, value in email_labels.items():
            if value > most_common_label:
                most_common_label = value
        for key, value in email_labels.items():
            # the email should mention the topic at least three times
            if value == most_common_label and value >= 3:
                self.rating -= 10
                if utils.settings.data["relay"]["save_statistics"]:
                    update_statistics(23)
                favorite_topic = collections.Counter(email_favorite_topics[key])
                favorite_topic = favorite_topic.most_common(1)[0][0]
                logging.info(
                    "[+] (salmonspam.py) - This email mostly talk about %s, especially %s"
                    % (spacy.explain(key).lower(), favorite_topic)
                )
                break

    @staticmethod
    def white_list(link):
        url_regex_pattern = r"^www\d{0,3}[.][a-z0-9\-]+[.][a-z]{2,4}$"
        r = re.match(url_regex_pattern, link)
        if r is not None and r.string:
            return True
        return False


def update_statistics(checkpoint_id):
    """Function changes the statistics about a checkpoint that
    changes the rating of the email.

    Args:
        checkpoint_id (int): Unique id for the checkpoint.
    """
    row = get_statistics_by_checkpoint_id(checkpoint_id)
    if row:
        update_statistics_counter(row)
    else:
        new_statistics_record = Statistics(
            checkpoint_id=checkpoint_id,
            counter=1,
            created=datetime.timestamp(datetime.today()),
            last_modified=datetime.timestamp(datetime.today()),
        )
        push_into_db(new_statistics_record)
