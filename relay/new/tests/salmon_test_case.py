import os
from salmon import utils
from salmon.salmondb import MailFields
from salmon.salmondb import push_into_db
from salmon.salmondb import MaybeTestMail
from salmon.salmondb import TestMail
from salmon.salmondb import Settings
from salmon.salmondb import Recipient
from salmon.salmondb import Link
from salmon.salmondb import Sender
from salmon import salmondb as db
from salmon.salmonmailparser import get_fuzzy_hash
from datetime import datetime
from essential_generators import DocumentGenerator
import pytest
import shutil
import string
import random
import logging
import logging.config


class SalmonTestCase(object):
    @classmethod
    def setup_class(cls):
        cls.generator = DocumentGenerator()

    @classmethod
    def teardown_class(cls):
        try:
            os.remove("testing_salmon.log")
        except FileNotFoundError as e:
            pass
        shutil.rmtree("./queue", ignore_errors=True)
        shutil.rmtree("./undeliverable", ignore_errors=True)

    def teardown_method(self):
        db.session.query(MailFields).delete()
        db.session.commit()

    @staticmethod
    def length(mail_fields):
        if mail_fields["html"]:
            return len(mail_fields["html"]) + len(mail_fields["subject"])
        elif mail_fields["text"]:
            return len(mail_fields["text"]) + len(mail_fields["subject"])
        else:
            return len(mail_fields["subject"])

    @pytest.fixture
    def f_subject(self):
        self.subject1 = self.generator.word()
        self.subject2 = self.generator.sentence()
        self.subject3 = self.generator.sentence()
        self.subject4 = " ".join([self.generator.word(), "changeme"])

    @pytest.fixture
    def f_body_plain(self):
        self.body_plain1 = self.generator.sentence()
        self.body_plain2 = self.generator.sentence()
        self.body_plain3 = self.generator.sentence()
        self.body_plain4 = " ".join([self.generator.word(), "changeme"])

    @pytest.fixture
    def f_body_html(self):
        self.body_html1 = self.generator.sentence()
        self.body_html2 = self.generator.sentence()
        self.body_html3 = self.generator.sentence()
        self.body_html4 = " ".join([self.generator.word(), "changeme"])

    @pytest.fixture
    def f_email(self):
        self.email1 = self.generator.email()
        self.email2 = self.generator.email()
        self.email3 = self.generator.email()
        self.email4 = self.generator.email()

    @pytest.fixture
    def f_name(self):
        self.name1 = " ".join([self.generator.word(), self.generator.word()])
        self.name2 = " ".join([self.generator.word(), self.generator.word()])
        self.name3 = " ".join([self.generator.word(), self.generator.word()])

    @pytest.fixture
    def f_ip(self):
        self.ip1 = "127.0.0.1"
        self.ip2 = "127.0.1.1"
        self.ip3 = "127.0.0.2"

    @pytest.fixture
    def f_password(self):
        letters = string.ascii_lowercase
        two_random_letters = "".join([random.choice(letters), random.choice(letters)])
        self.password1 = " ".join([self.generator.word(), two_random_letters])
        self.password2 = " ".join([self.generator.word(), two_random_letters])
        self.password3 = " ".join([self.generator.word(), two_random_letters])

    @pytest.fixture
    def f_username(self):
        letters = string.ascii_lowercase
        two_random_letters = "".join([random.choice(letters), random.choice(letters)])
        self.username1 = " ".join([self.generator.word(), two_random_letters])
        self.username2 = " ".join([self.generator.word(), two_random_letters])
        self.username3 = " ".join([self.generator.word(), two_random_letters])

    @pytest.fixture
    def f_link(self):
        self.link1 = self.generator.url()
        self.link2 = self.generator.url()
        self.link3 = self.generator.url()

    @pytest.fixture
    def f_mail_fields_dict(self, f_subject, f_body_plain, f_body_html, f_email):
        self.mail_fields_dict1 = {
            "text": self.body_plain1,
            "subject": self.subject1,
            "html": self.body_html1,
            "from": self.email1,
        }
        self.mail_fields_dict2 = {
            "text": self.body_plain2,
            "subject": self.subject2,
            "html": self.body_html2,
            "from": self.email2,
        }
        self.mail_fields_dict3 = {
            "text": self.body_plain3,
            "subject": self.subject3,
            "html": self.body_html3,
            "from": self.email3,
        }
        self.mail_fields_dict4 = {
            "text": self.body_plain4,
            "subject": self.subject4,
            "html": self.body_html4,
            "from": self.email4,
        }

    @pytest.fixture
    def f_mail_fields(self, f_mail_fields_dict):
        self.mail_fields1 = MailFields(
            subject=self.subject1,
            email_date=datetime.timestamp(datetime.today()),
            body_html=self.body_html1,
            ssdeep=get_fuzzy_hash(self.mail_fields_dict1),
            length=self.length(self.mail_fields_dict1),
            attachment=False,
        )
        self.mail_fields2 = MailFields(
            subject=self.subject2,
            email_date=datetime.timestamp(datetime.today()),
            body_plain=self.body_plain2,
            ssdeep=get_fuzzy_hash(self.mail_fields_dict2),
            length=self.length(self.mail_fields_dict2),
            attachment=False,
        )
        self.mail_fields3 = MailFields(
            subject=self.subject3,
            email_date=datetime.timestamp(datetime.today()),
            body_plain=self.body_plain3,
            body_html=self.body_html3,
            ssdeep=get_fuzzy_hash(self.mail_fields_dict3),
            length=self.length(self.mail_fields_dict3),
            attachment=True,
        )
        self.mail_fields4 = MailFields(
            subject=self.subject4,
            email_date=datetime.timestamp(datetime.today()),
            body_plain=self.body_plain4,
            body_html=self.body_html4,
            ssdeep=get_fuzzy_hash(self.mail_fields_dict4),
            length=self.length(self.mail_fields_dict4),
            attachment=False,
        )
        self.mail_fields_list = [
            self.mail_fields1,
            self.mail_fields2,
            self.mail_fields3,
            self.mail_fields4,
        ]
        for mf in self.mail_fields_list:
            push_into_db(mf)

    @pytest.fixture
    def f_maybe_test_emails(self, f_mail_fields):
        self.f_maybe_test_email1 = MaybeTestMail(
            rating=50,
            in_db_date=datetime.timestamp(datetime.today()),
            mailfield=self.mail_fields1,
        )
        self.f_maybe_test_email2 = MaybeTestMail(
            rating=60,
            in_db_date=datetime.timestamp(datetime.today()),
            mailfield=self.mail_fields2,
        )
        self.f_maybe_test_email3 = MaybeTestMail(
            rating=65,
            in_db_date=datetime.timestamp(datetime.today()),
            mailfield=self.mail_fields3,
        )
        self.maybe_test_emails_list = [
            self.f_maybe_test_email1,
            self.f_maybe_test_email2,
            self.f_maybe_test_email3,
        ]

    @pytest.fixture
    def f_test_emails(self, f_mail_fields):
        self.f_test_email1 = TestMail(mailfield=self.mail_fields1)
        self.f_test_email2 = TestMail(mailfield=self.mail_fields2)
        self.f_test_email3 = TestMail(mailfield=self.mail_fields3)
        self.test_emails_list = [
            self.f_test_email1,
            self.f_test_email2,
            self.f_test_email3,
        ]

    @pytest.fixture
    def f_settings(self, f_username, f_password):
        self.settings1 = Settings(username=self.username1, password=self.password1)
        self.settings2 = Settings(username=self.username2, password=self.password2)
        self.settings3 = Settings(username=self.username3, password=self.password3)
        self.settings_list = [self.settings1, self.settings2, self.settings3]

    @pytest.fixture
    def f_recipient(self, f_name, f_email, f_mail_fields):
        self.recipient1 = Recipient(
            email=self.email1, name=self.name1, mailfield=self.mail_fields1
        )
        self.recipient2 = Recipient(
            email=self.email2, name=self.name2, mailfield=self.mail_fields2
        )
        self.recipient3 = Recipient(
            email=self.email3, name=self.name3, mailfield=self.mail_fields3
        )
        self.recipients_list = [self.recipient1, self.recipient2, self.recipient3]

    @pytest.fixture
    def f_sender(self, f_name, f_email, f_mail_fields):
        self.sender1 = Sender(
            email=self.email1, name=self.name1, mailfield=self.mail_fields1
        )

    @pytest.fixture
    def f_links(self, f_link):
        self.f_link1 = Link(self.link1, 1, 50)
        self.f_link2 = Link(self.link2, 2, 55)
        self.f_link3 = Link(self.link3, 3, 60)
        self.links_list = [self.f_link1, self.f_link2, self.f_link3]
