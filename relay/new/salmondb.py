"""Salmon database module.

This module contains database tables and contains operations that can be performed on them.
Author: Silvie Chlupová
Date    Created: 03/31/2020
"""

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import Float
from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import backref
from salmon.base import Base
from salmon.base import Session
from salmon.base import engine
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging
import os


"""
    ---------------------------
    SQL ORM MODELS DECLARATION
    ---------------------------
"""
class MailFields(Base):
    """Data model for email fields."""

    __tablename__ = "mail_fields"

    id = Column(Integer, autoincrement=True, primary_key=True)
    subject = Column(String(512), nullable=True)
    email_date = Column(String(512), nullable=False)
    body_plain = Column(String(512), nullable=True)
    body_html = Column(String(512), nullable=True)
    ssdeep = Column(String(512), nullable=False)
    length = Column(Integer, nullable=False)
    attachment = Column(Boolean, nullable=False)

    def __init__(
        self,
        email_date,
        ssdeep,
        length,
        attachment,
        body_plain="",
        body_html="",
        subject="",
    ):
        self.subject = subject
        self.email_date = email_date
        self.body_plain = body_plain
        self.body_html = body_html
        self.ssdeep = ssdeep
        self.length = length
        self.attachment = attachment

    def __repr__(self):
        return "[+] (salmondb.py) - Adding new email fields with id {}.".format(self.id)


class MaybeTestMail(Base):
    """Data model for maybe test email."""

    __tablename__ = "maybe_test_emails"

    id = Column(Integer, primary_key=True)
    rating = Column(Integer, nullable=False)
    in_db_date = Column(Float, nullable=False)
    mail_fields_id = Column(Integer, ForeignKey("mail_fields.id"))
    mailfield = relationship(
        "MailFields", backref=backref("maybe_test_emails", cascade="all, delete-orphan")
    )

    def __init__(self, rating, in_db_date, mailfield):
        self.rating = rating
        self.in_db_date = in_db_date
        self.mailfield = mailfield

    def __repr__(self):
        return "[+] (salmondb.py) - Adding new maybe testing email with id {}.".format(self.id)


class TestMail(Base):
    """Data model for test email."""

    __tablename__ = "test_emails"

    id = Column(Integer, primary_key=True)
    mail_fields_id = Column(Integer, ForeignKey("mail_fields.id"))
    mailfield = relationship("MailFields", backref="test_emails")

    def __init__(self, mailfield):
        self.mailfield = mailfield

    def __repr__(self):
        return "[+] (salmondb.py) - Adding new testing email with id {}.".format(self.id)


class Settings(Base):
    """Data model for honeypot credentials."""

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    username = Column(String(128), nullable=False)
    password = Column(String(128), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __repr__(self):
        return "[+] (salmondb.py) - Adding new credentials ({0}, {1}).".format(self.username, self.password)


class Recipient(Base):
    """Data model for recipient."""

    __tablename__ = "recipient"

    id = Column(Integer, primary_key=True)
    email = Column(String(512), nullable=False)
    name = Column(String(512), nullable=False)
    mail_fields_id = Column(Integer, ForeignKey("mail_fields.id"))
    mailfield = relationship("MailFields", backref="recipient")

    def __init__(self, email, name, mailfield):
        self.email = email
        self.name = name
        self.mailfield = mailfield

    def __repr__(self):
        return "[+] (salmondb.py) - Adding new recipient {}.".format(self.email)


class Link(Base):
    """Data model for link."""

    __tablename__ = "link"

    id = Column(Integer, primary_key=True)
    link = Column(String(512), nullable=False)
    counter = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False)

    def __init__(self, link, counter, rating):
        self.link = link
        self.counter = counter
        self.rating = rating

    def __repr__(self):
        return "[+] (salmondb.py) - link {0} with counter {1}.".format(self.link, self.counter)


class Sender(Base):
    """Data model for sender."""

    __tablename__ = "sender"

    id = Column(Integer, primary_key=True)
    email = Column(String(512), nullable=False)
    name = Column(String(512), nullable=False)
    mail_fields_id = Column(Integer, ForeignKey("mail_fields.id"))
    mailfield = relationship("MailFields", backref="sender")

    def __init__(self, email, name, mailfield):
        self.email = email
        self.name = name
        self.mailfield = mailfield

    def __repr__(self):
        return "[+] (salmondb.py) - Adding new sender {}.".format(self.email)


class Statistics(Base):
    """Data model for statistics."""

    __tablename__ = "statistics"

    id = Column(Integer, primary_key=True)
    checkpoint_id = Column(Integer, nullable=False)
    counter = Column(Integer, nullable=False)
    created = Column(Float, nullable=False)
    last_modified = Column(Float, nullable=False)

    def __init__(self, checkpoint_id, counter, created, last_modified):
        self.checkpoint_id = checkpoint_id
        self.counter = counter
        self.created = created
        self.last_modified = last_modified


"""
    ---------------------------
    SQL OPERATIONS
    ---------------------------
"""
session = Session()
cwd = os.getcwd()
path, project = os.path.split(cwd)
if engine.url.database == "salmon.db" and project != "myproject":
    raise Exception("Run salmon only from the myproject directory!")
elif engine.url.database == "testing_salmon.db" and project != "tests":
    raise Exception("Run tests only from the tests directory!")
Base.metadata.create_all(engine)


def push_into_db(obj_into_db):
    """This pushes one of the models into the database.

    Args:
        obj_into_db: One of the SQL models.
    """
    session.add(obj_into_db)

    try:
        session.commit()
    except SQLAlchemyError as error:
        logging.error(error)
        logging.error("[-] (salmondb.py) - Error occurred during pushing into the database.")
    else:
        if not isinstance(obj_into_db, Statistics):
            logging.info(obj_into_db)


def push_email_into_db(mail_fields, email, recipients, sender):
    """Function pushes email into the database which means that it pushes
    email fields model, TestMail or MaybeTestMail model, Recipient model and Sender model.

    Args:
        mail_fields (MailFields): Database model of parsed email fields.
        email (TestMail): Instance of the TestMail class with ids of the test emails.
        recipients (Recipient): List of instances of the Recipient class.
        sender (Sender): Instance of the Sender class.
    """
    logging.info("[+] (salmondb.py) - Pushing new maybe test email into the database.")
    push_into_db(mail_fields)
    push_into_db(email)
    for recipient in recipients:
        push_into_db(recipient)
    push_into_db(sender)


def are_credentials_in_db(username, password):
    """Checks if the honeypot credentials are in the database.

    Args:
        username (str): Honeypot username.
        password (str): Honeypot password.

    Returns:
        bool: True if credentials are already in the database, False otherwise.
    """
    credentials_from_db = session.query(Settings).all()
    for credentials in credentials_from_db:
        if credentials.username == username and credentials.password == password:
            logging.debug(
                "[+] (salmondb.py) - %s, %s are already in the database." % (username, password)
            )
            return True
    return False


def get_passwords():
    """Returns the honeypot passwords stored in the database."""
    passwords = []
    for credentials in session.query(Settings).all():
        passwords.append(credentials.password)
    return passwords


def get_usernames():
    """Returns the honeypot usernames stored in the database."""
    usernames = []
    for credentials in session.query(Settings).all():
        usernames.append(credentials.username)
    return usernames


def get_mail_fields():
    """Returns all email fields stored in the database as a MailFields model."""
    mail_fields = []
    for fields in session.query(MailFields).all():
        mail_fields.append(fields)
    return mail_fields


def get_recipients():
    """Returns all recipients stored in the database."""
    recipients = []
    for recipient in session.query(Recipient).all():
        recipients.append(recipient)
    return recipients


def get_links():
    """Returns all links stored in the database."""
    links = []
    for link in session.query(Link).all():
        links.append(link)
    return links


def get_statistics():
    """Returns the honeypot statistics stored in the database."""
    s = []
    for st in session.query(Statistics).all():
        s.append(st)
    return s


def get_link_by_name(link):
    """Returns a specific link stored in the database."""
    return session.query(Link).filter(Link.link == link).first()


def update_link_counter(row):
    """Updates the counter of a specific link in the database."""
    row.counter += 1
    session.commit()


def update_link_rating(row, new_rating):
    """Updates the rating of a specific link in the database."""
    row.rating = new_rating
    session.commit()


def update_statistics_counter(row):
    """Updates the counter of a specific info the in statistics in the database."""
    row.counter += 1
    row.last_modified = datetime.timestamp(datetime.today())
    session.commit()
    logging.debug(
        "[+] (salmondb.py) - Updating checkpoint %d." % row.checkpoint_id
    )


def get_recipient_by_email(email):
    """Returns the specific recipient stored in the database."""
    return session.query(Recipient).filter(Recipient.email == email).first()


def get_statistics_by_checkpoint_id(checkpoint_id):
    """Returns a specific statistics info (e.g. email with attachment) stored in the database."""
    return session.query(Statistics).filter(Statistics.checkpoint_id == checkpoint_id).first()


def get_testmail_by_mailfield_id(id):
    """Returns a specific test email stored in the database."""
    return session.query(TestMail).filter(TestMail.mail_fields_id == id).first()


def get_maybetestmail_by_mailfield_id(id):
    """Returns a specific maybe test email stored in the database."""
    return (
        session.query(MaybeTestMail).filter(MaybeTestMail.mail_fields_id == id).first()
    )


def get_mail_fields_by_id(id):
    """Returns the specific email fields stored in the database."""
    return session.query(MailFields).filter(MailFields.id == id).first()


def email_into_db(rating, database_mail_fields, recipient_model_list, sender):
    """Pushes a maybe test email into the database.

    Args:
        rating (int): Final email rating.
        database_mail_fields (MailFields): Database model of parsed email fields.
        recipient_model_list (List[Recipient]): List of email recipients.
        sender (Sender): Instance of the Sender class.
    """
    maybe_test_email = MaybeTestMail(
        rating, datetime.timestamp(datetime.today()), database_mail_fields,
    )
    push_email_into_db(
        database_mail_fields, maybe_test_email, recipient_model_list, sender,
    )


def move_to_testmail(mail_fields_id):
    """Moves email saved as maybe test email to the test_emails table.

    Args:
        mail_fields_id (int): Id of the record in the table for email fields.
    """
    database_mail_fields = get_mail_fields_by_id(mail_fields_id)
    delete_maybetestmail_record(mail_fields_id)
    test_mail = TestMail(database_mail_fields)
    push_into_db(test_mail)


def delete_maybetestmail_record(mail_fields_id):
    """Deletes a record from the table for email fields.

    Args:
        mail_fields_id (int): Id of the record in the table for email fields.
    """
    selected_mail = session.query(MaybeTestMail).filter(MaybeTestMail.mail_fields_id == mail_fields_id)
    selected_mail.delete()
    session.commit()
    logging.info("[+] (salmondb.py) - Deleting a record from the maybe_test_emails table.")

session.close()
