from salmon.salmonconclude import conclude
from salmon.salmonconclude import Spam
from salmon.salmonmailparser import process_email
from salmon.salmonmailparser import get_fuzzy_hash
from salmon.salmondb import push_into_db
from salmon.salmondb import push_email_into_db
from salmon.salmondb import Settings
from salmon.salmondb import TestMail
from salmon.salmondb import MaybeTestMail
from salmon.salmondb import Settings
from salmon.salmondb import Recipient
from salmon.salmondb import Link
from salmon.salmondb import Sender
from salmon.salmondb import MailFields
from salmon import salmondb as db
from tests.salmon_test_case import SalmonTestCase
from salmon.mail import MailRequest
from datetime import datetime
from salmon import utils
import pytest
import os
import json


class TestSalmonConclude(SalmonTestCase):
    eml_file1 = "{ip}-salmon-user".format(ip="192.168.122.5")

    def setup_method(self):
        utils.import_settings(True, boot_module="tests.testing_boot")
        self.ip = "127.0.0.1"
        utils.settings.data["receiver"]["listenhost"] = self.ip
        self.fake_mail_request = MailRequest("", None, None, "")
        self.fake_eml_file = "{ip}-salmon-user".format(ip=self.ip)
        self.file1 = "./rawspams/{}".format(self.eml_file1)

    def teardown_method(self):
        for table in [
            Settings,
            TestMail,
            MailFields,
            MaybeTestMail,
            Recipient,
            Sender,
            Link,
        ]:
            db.session.query(table).delete()
        db.session.commit()

    @staticmethod
    def eml_content(file_name):
        with open("./rawspams/{}".format(file_name), "rb") as f:
            content = f.read()
        return content

    def test_rating_100_1(self, f_password):
        """Test email with the password in body_plain"""
        self.password4 = "changeme"
        self.username4 = "changeme"
        self.settings4 = Settings(username=self.username4, password=self.password4)
        push_into_db(self.settings4)
        mail_request = MailRequest(
            self.eml_file1, None, None, self.eml_content(self.eml_file1)
        )
        mail_fields = process_email(self.eml_file1, mail_request)
        rating = conclude(mail_fields, self.eml_file1, mail_request)
        assert rating == 100

    def test_rating_100_2(self, f_sender, f_recipient, f_mail_fields_dict):
        """Test email which already in test_emails table in db"""
        test_email = TestMail(self.mail_fields1)
        push_email_into_db(
            self.mail_fields1, test_email, [self.recipient1], self.sender1
        )
        self.mail_fields_dict5 = {
            "text": " ".join([self.body_plain1]),
            "html": "",
            "subject": self.subject1,
            "from": self.email1,
            "from_name": "",
            "to": [(self.email1, self.name1)],
            "date": 1587298372.484211,
            "attachmentFileName": [],
            "links": [],
        }
        self.mail_fields_dict5["len"] = (
            len(self.mail_fields_dict5["html"])
            + len(self.mail_fields_dict5["subject"])
            + len(self.mail_fields_dict5["text"])
        )
        self.mail_fields_dict5["ssdeep"] = get_fuzzy_hash(self.mail_fields_dict5)
        rating = conclude(
            self.mail_fields_dict5, self.fake_eml_file, self.fake_mail_request
        )
        assert rating == 100

    def test_rating_55(self, f_settings, f_mail_fields_dict):
        """Test email with the username in body_plain and test time"""
        push_into_db(self.settings1)
        self.mail_fields_dict5 = {
            "text": " ".join([self.body_plain1, self.username1]),
            "html": "",
            "subject": self.subject1,
            "from": self.email1,
            "from_name": "",
            "to": [(self.email2, "")],
            "date": 1587298372.484211,
            "attachmentFileName": [],
            "links": [],
        }
        self.mail_fields_dict5["len"] = (
            len(self.mail_fields_dict5["html"])
            + len(self.mail_fields_dict5["subject"])
            + len(self.mail_fields_dict5["text"])
        )
        self.mail_fields_dict5["ssdeep"] = get_fuzzy_hash(self.mail_fields_dict5)
        rating = conclude(
            self.mail_fields_dict5, self.fake_eml_file, self.fake_mail_request
        )
        assert rating == 55

    def test_rating_30(self, f_settings, f_mail_fields_dict):
        """Test email with the username in body_plain, body_plain is very long"""
        push_into_db(self.settings1)
        self.body_plain5 = (
            self.generator.paragraph() + "\n" + self.generator.paragraph()
        )
        self.mail_fields_dict5 = {
            "text": " ".join([self.body_plain5, self.username1]),
            "html": "",
            "subject": self.subject1,
            "from": self.email1,
            "from_name": "",
            "to": [(self.email2, "")],
            "date": 1587322973.484211,
            "attachmentFileName": [],
            "links": [],
        }
        self.mail_fields_dict5["len"] = (
            len(self.mail_fields_dict5["html"])
            + len(self.mail_fields_dict5["subject"])
            + len(self.mail_fields_dict5["text"])
        )
        self.mail_fields_dict5["ssdeep"] = get_fuzzy_hash(self.mail_fields_dict5)
        rating = conclude(
            self.mail_fields_dict5, self.fake_eml_file, self.fake_mail_request
        )
        assert rating == 30

    def test_rating_40(self, f_settings, f_mail_fields_dict):
        """Test email with the username in body_plain and attachment"""
        push_into_db(self.settings2)
        self.mail_fields_dict5 = {
            "text": " ".join([self.body_plain2, self.username2]),
            "html": "",
            "subject": self.subject1,
            "from": self.email1,
            "from_name": "",
            "to": [(self.email2, "")],
            "date": 1587322973.484211,
            "attachmentFileName": ["test.doc"],
            "links": [],
        }
        self.mail_fields_dict5["len"] = (
            len(self.mail_fields_dict5["html"])
            + len(self.mail_fields_dict5["subject"])
            + len(self.mail_fields_dict5["text"])
        )
        self.mail_fields_dict5["ssdeep"] = get_fuzzy_hash(self.mail_fields_dict5)
        rating = conclude(
            self.mail_fields_dict5, self.fake_eml_file, self.fake_mail_request
        )
        assert rating == 40

    def test_rating_45(self, f_link, f_settings, f_mail_fields_dict):
        """Test email with link and username in body_plain and test time"""
        push_into_db(self.settings1)
        self.mail_fields_dict5 = {
            "text": " ".join([self.body_plain1, self.username1, self.link1]),
            "html": "",
            "subject": self.subject1,
            "from": self.email1,
            "from_name": "",
            "to": [(self.email2, "")],
            "date": 1587298372.484211,
            "attachmentFileName": [],
            "links": [self.link1],
        }
        self.mail_fields_dict5["len"] = (
            len(self.mail_fields_dict5["html"])
            + len(self.mail_fields_dict5["subject"])
            + len(self.mail_fields_dict5["text"])
        )
        self.mail_fields_dict5["ssdeep"] = get_fuzzy_hash(self.mail_fields_dict5)
        rating = conclude(
            self.mail_fields_dict5, self.fake_eml_file, self.fake_mail_request
        )
        assert rating == 45

    def test_rating_50(self, f_links, f_settings, f_mail_fields_dict):
        """Test email with link (which is already in db three times) 
        and username in body_plain"""
        push_into_db(self.settings1)
        self.f_link4 = Link(self.link2, 3, 60)
        push_into_db(self.f_link4)
        self.mail_fields_dict5 = {
            "text": " ".join([self.body_plain1, self.username1, self.link2]),
            "html": "",
            "subject": self.subject1,
            "from": self.email1,
            "from_name": "",
            "to": [(self.email2, "")],
            "date": 1587322973.484211,
            "attachmentFileName": [],
            "links": [self.link2],
        }
        self.mail_fields_dict5["len"] = (
            len(self.mail_fields_dict5["html"])
            + len(self.mail_fields_dict5["subject"])
            + len(self.mail_fields_dict5["text"])
        )
        self.mail_fields_dict5["ssdeep"] = get_fuzzy_hash(self.mail_fields_dict5)
        rating = conclude(
            self.mail_fields_dict5, self.fake_eml_file, self.fake_mail_request
        )
        assert rating == 50

    def test_rating_0(self, f_settings, f_mail_fields_dict):
        """Test email with attachment and word test in subject"""
        push_into_db(self.settings1)
        self.mail_fields_dict5 = {
            "text": " ".join([self.body_plain2]),
            "html": "",
            "subject": " ".join(["test"]),
            "from": self.email1,
            "from_name": "",
            "to": [(self.email2, "")],
            "date": 1587322973.484211,
            "attachmentFileName": ["test.doc"],
            "links": [],
        }
        self.mail_fields_dict5["len"] = (
            len(self.mail_fields_dict5["html"])
            + len(self.mail_fields_dict5["subject"])
            + len(self.mail_fields_dict5["text"])
        )
        self.mail_fields_dict5["ssdeep"] = get_fuzzy_hash(self.mail_fields_dict5)
        rating = conclude(
            self.mail_fields_dict5, self.fake_eml_file, self.fake_mail_request
        )
        assert rating == 0

    def test_rating_70(self, f_mail_fields_dict):
        """Test email with honeypot IP address in subject"""
        self.mail_fields_dict5 = {
            "text": " ".join([self.body_plain2]),
            "html": "",
            "subject": self.ip,
            "from": self.email1,
            "from_name": "",
            "to": [(self.email2, "")],
            "date": 1587322973.484211,
            "attachmentFileName": [],
            "links": [],
        }
        self.mail_fields_dict5["len"] = (
            len(self.mail_fields_dict5["html"])
            + len(self.mail_fields_dict5["subject"])
            + len(self.mail_fields_dict5["text"])
        )
        self.mail_fields_dict5["ssdeep"] = get_fuzzy_hash(self.mail_fields_dict5)
        rating = conclude(
            self.mail_fields_dict5, self.fake_eml_file, self.fake_mail_request
        )
        assert rating == 70

    def test_similar_email_in_db(self, f_sender, f_recipient, f_mail_fields_dict):
        """Similar test email is already in the database"""
        test_email = TestMail(self.mail_fields1)
        push_email_into_db(
            self.mail_fields1, test_email, [self.recipient1], self.sender1
        )
        self.mail_fields_dict5 = {
            "text": " ".join([self.body_plain1]),
            "html": "",
            "subject": self.subject1,
            "from": self.email1,
            "from_name": "",
            "to": [(self.email1, self.name1)],
            "date": 1587298372.484211,
            "attachmentFileName": [],
            "links": [],
        }
        self.mail_fields_dict5["len"] = (
            len(self.mail_fields_dict5["html"])
            + len(self.mail_fields_dict5["subject"])
            + len(self.mail_fields_dict5["text"])
        )
        self.mail_fields_dict5["ssdeep"] = get_fuzzy_hash(self.mail_fields_dict5)
        spam = Spam(
            subject=str(self.mail_fields_dict5["subject"]),
            email_date=str(self.mail_fields_dict5["date"]),
            body_plain=self.mail_fields_dict5["text"],
            body_html=self.mail_fields_dict5["html"],
            ssdeep=self.mail_fields_dict5["ssdeep"],
            length=self.mail_fields_dict5["len"],
            attachment=False,
        )
        similar_emails_ids = spam.get_ids_for_similarity_check()
        assert similar_emails_ids[0] == 1

    def test_rating_100_3(self, f_mail_fields_dict):
        """Match against the rule file"""
        utils.settings.data["relay"]["use_rule_file"] = True
        with open("./testing_rules.json") as json_file:
            utils.settings.rules = json.load(json_file)
        self.mail_fields_dict5 = {
            "text": "example body_plain",
            "html": "",
            "subject": self.subject1,
            "from": self.email1,
            "from_name": "",
            "to": [(self.email2, "")],
            "date": 1587298372.484211,
            "attachmentFileName": [],
            "links": [],
        }
        self.mail_fields_dict5["len"] = (
            len(self.mail_fields_dict5["html"])
            + len(self.mail_fields_dict5["subject"])
            + len(self.mail_fields_dict5["text"])
        )
        self.mail_fields_dict5["ssdeep"] = get_fuzzy_hash(self.mail_fields_dict5)
        rating = conclude(
            self.mail_fields_dict5, self.fake_eml_file, self.fake_mail_request
        )
        assert rating == 100
