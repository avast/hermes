from salmon.salmonmailparser import process_email
from salmon.salmonmailparser import get_fuzzy_hash
from salmon.salmonmailparser import move_to_undeliverable
from tests.salmon_test_case import SalmonTestCase
from salmon.mail import MailRequest
import ssdeep
import pytest
import logging
import shutil
from salmon import utils
from pathlib import Path
import os


class TestSalmonMailParser(SalmonTestCase):
    eml_file1 = "{ip}-salmon-user".format(ip="192.168.122.1")
    eml_file2 = "{ip}-salmon-user".format(ip="192.168.122.2")
    eml_file3 = "{ip}-salmon-user".format(ip="192.168.122.3")
    eml_file4 = "{ip}-salmon-user".format(ip="192.168.122.4")

    @classmethod
    def setup_class(cls):
        Path("./queue").mkdir(parents=True, exist_ok=True)
        Path("./queue/new").mkdir(parents=True, exist_ok=True)
        Path("./undeliverable").mkdir(parents=True, exist_ok=True)
        Path("./attachments").mkdir(parents=True, exist_ok=True)
        utils.import_settings(True, boot_module="tests.testing_boot")

    @classmethod
    def teardown_class(cls):
        os.remove("testing_salmon.log")
        shutil.rmtree("./queue", ignore_errors=True)
        shutil.rmtree("./queue/new", ignore_errors=True)
        shutil.rmtree("./undeliverable", ignore_errors=True)
        shutil.rmtree("./attachments", ignore_errors=True)

    def setup_method(self):
        shutil.copyfile(
            "./rawspams/{}".format(self.eml_file1),
            "./queue/new/{}".format(self.eml_file1),
        )
        shutil.copyfile(
            "./rawspams/{}".format(self.eml_file2),
            "./queue/new/{}".format(self.eml_file2),
        )
        shutil.copyfile(
            "./rawspams/{}".format(self.eml_file3),
            "./queue/new/{}".format(self.eml_file3),
        )
        shutil.copyfile(
            "./rawspams/{}".format(self.eml_file4),
            "./queue/new/{}".format(self.eml_file4),
        )

    def teardown_method(self):
        os.remove("./queue/new/{}".format(self.eml_file1))
        os.remove("./queue/new/{}".format(self.eml_file2))
        os.remove("./queue/new/{}".format(self.eml_file3))
        os.remove("./queue/new/{}".format(self.eml_file4))

    @staticmethod
    def eml_content(file_name):
        with open("./rawspams/{}".format(file_name), "rb") as f:
            content = f.read()
        return content

    def test_mail_fields(self):
        mail_request = MailRequest(
            self.eml_file1, None, None, self.eml_content(self.eml_file1)
        )
        mail_fields = process_email(self.eml_file1, mail_request)
        assert isinstance(mail_fields, dict)
        assert mail_fields["to"][0][0] == "test@test.com"
        assert mail_fields["reply-to"] == "test@test.com"
        assert mail_fields["from"] == "test@test.com"
        assert mail_fields["from_name"] == "Test Test"
        assert mail_fields["subject"] == "Hello"
        assert mail_fields["text"] == "test"

    def test_eml_without_attachment(self):
        mail_request = MailRequest(
            self.eml_file1, None, None, self.eml_content(self.eml_file1)
        )
        mail_fields = process_email(self.eml_file1, mail_request)
        assert isinstance(mail_fields, dict)
        assert len(mail_fields["attachmentFileName"]) == 0

    def test_move_to_undeliverable(self):
        move_to_undeliverable(self.eml_file1)
        assert len(os.listdir('./undeliverable')) == 1
        assert os.listdir('./undeliverable')[0] == self.eml_file1

    def test_eml_with_attachment(self):
        mail_request = MailRequest(
            self.eml_file2, None, None, self.eml_content(self.eml_file2)
        )
        mail_fields = process_email(self.eml_file2, mail_request)
        assert isinstance(mail_fields, dict)
        assert len(mail_fields["attachmentFileName"]) == 1
        assert mail_fields["attachmentFileName"][0] == "my_attach.doc"

    def test_bad_reply_to(self):
        mail_request = MailRequest(
            self.eml_file2, None, None, self.eml_content(self.eml_file2)
        )
        mail_fields = process_email(self.eml_file2, mail_request)
        assert isinstance(mail_fields, dict)
        assert mail_fields["reply-to"] == "-"

    def test_link_in_eml(self):
        mail_request = MailRequest(
            self.eml_file3, None, None, self.eml_content(self.eml_file3)
        )
        mail_fields = process_email(self.eml_file3, mail_request)
        assert isinstance(mail_fields, dict)
        assert len(mail_fields["links"]) > 0
        assert mail_fields["links"][0] == "www.test.cz"

    def test_eml_with_inline(self):
        mail_request = MailRequest(
            self.eml_file4, None, None, self.eml_content(self.eml_file4)
        )
        mail_fields = process_email(self.eml_file4, mail_request)
        assert len(mail_fields["attachmentFileName"]) == 1
        assert mail_fields["attachmentFileName"][0] == None
