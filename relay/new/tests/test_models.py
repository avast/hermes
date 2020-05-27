from salmon.salmonmailparser import process_email
from salmon.salmonmailparser import get_fuzzy_hash
from salmon.salmondb import get_mail_fields
from salmon.salmondb import MailFields
from salmon.salmondb import get_maybetestmail_by_mailfield_id
from salmon.salmondb import get_testmail_by_mailfield_id
from salmon.salmondb import are_credentials_in_db
from salmon.salmondb import get_passwords
from salmon.salmondb import get_usernames
from salmon.salmondb import get_recipients
from salmon.salmondb import get_links
from salmon.salmondb import get_link_by_name
from salmon.salmondb import update_link_counter
from tests.salmon_test_case import SalmonTestCase
from salmon.salmondb import push_into_db
import ssdeep


class TestSalmonModel(SalmonTestCase):
    def test_db_mail_fields_create(self, f_mail_fields):
        assert self.mail_fields1.subject == self.subject1
        compare = ssdeep.compare(
            get_fuzzy_hash(self.mail_fields_dict1), self.mail_fields1.ssdeep
        )
        assert compare == 100
        assert self.mail_fields3.attachment

    def test_db_mail_fields_read(self, f_mail_fields):
        db_mail_fields = get_mail_fields()
        assert len(db_mail_fields) == 4
        for mf in db_mail_fields:
            if self.mail_fields2.subject == mf.subject:
                assert mf.body_plain == self.body_plain2
                assert mf.length == self.length(self.mail_fields_dict2)
            elif self.mail_fields3.subject == mf.subject:
                assert mf.body_plain == self.body_plain3
                assert mf.length == self.length(self.mail_fields_dict3)
            elif self.mail_fields4.subject == mf.subject:
                assert mf.body_plain == self.body_plain4
                assert mf.length == self.length(self.mail_fields_dict4)

    def test_db_maybe_test_mail_create(self, f_maybe_test_emails):
        assert isinstance(self.f_maybe_test_email1.mailfield, MailFields)
        assert self.f_maybe_test_email1.mailfield.id == self.mail_fields1.id
        assert self.f_maybe_test_email3.mailfield.id == self.mail_fields3.id

    def test_db_maybe_test_mail_read(self, f_maybe_test_emails):
        for email in self.maybe_test_emails_list:
            push_into_db(email)
        email = get_maybetestmail_by_mailfield_id(2)
        assert email.id == 2
        assert email.mailfield.subject == self.subject2

    def test_db_test_mail_create(self, f_test_emails):
        assert isinstance(self.f_test_email1.mailfield, MailFields)
        assert self.f_test_email1.mailfield.id == self.mail_fields1.id
        assert self.f_test_email2.mailfield.id == self.mail_fields2.id

    def test_db_test_mail_read(self, f_test_emails):
        for email in self.test_emails_list:
            push_into_db(email)
        email = get_testmail_by_mailfield_id(1)
        assert email.id == 1
        assert email.mailfield.subject == self.subject1

    def test_db_settings_create(self, f_settings):
        assert self.settings1.username == self.username1
        assert self.settings2.password == self.password2
        assert self.settings3.username == self.username3

    def test_db_settings_read(self, f_settings):
        for settings in self.settings_list:
            push_into_db(settings)
        db_passwords = get_passwords()
        db_usernames = get_usernames()
        assert are_credentials_in_db(self.settings1.username, self.settings1.password)
        assert db_passwords[0] == self.password1
        assert db_usernames[0] == self.username1
        assert db_passwords[1] == self.password2
        assert db_usernames[1] == self.username2
        assert db_passwords[2] == self.password3
        assert db_usernames[2] == self.username3

    def test_db_recipient_create(self, f_recipient):
        assert self.recipient1.email == self.email1
        assert self.recipient2.name == self.name2
        assert self.recipient3.name == self.name3

    def test_db_recipient_read(self, f_recipient):
        for recipient in self.recipients_list:
            push_into_db(recipient)
        db_recipients = get_recipients()
        assert db_recipients[3].email == self.email1
        assert db_recipients[4].name == self.name2

    def test_db_link_read(self, f_links):
        assert self.f_link1.link == self.link1
        for link in self.links_list:
            push_into_db(link)
        links = get_links()
        assert links[0].link == self.f_link1.link
        assert links[1].link == self.f_link2.link
        assert links[2].rating == 60
        link = get_link_by_name(self.f_link1.link)
        assert link.counter == 1
        update_link_counter(self.f_link2)
        link = get_link_by_name(self.f_link2.link)
        assert link.counter == 3
