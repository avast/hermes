#!/usr/bin/env python3

"""salmondeleteold module.

This module deletes one-month-old records from the maybe_test_emails table in the database.
Author: Silvie Chlupová
Date    Created: 05/16/2020
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from salmon.salmondb import MaybeTestMail
from datetime import datetime

def get_maybetestmails(session):
    """Returns all maybe test e-mails stored in the database."""
    mails = []
    for mail in session.query(MaybeTestMail).all():
        mails.append(mail)
    return mails


def delete_old_from_maybetestmail(mails):
    """Delete 30 days old records from the maybe_test_emails table."""
    today = datetime.timestamp(datetime.today())
    to_delete = []
    for mail in mails:
        delta = today - mail.in_db_date
        if delta >= 2592000:
            to_delete.append(mail.id)
    for id in to_delete:
        selected_mail = session.query(MaybeTestMail).filter(MaybeTestMail.id == id)
        selected_mail.delete()
        session.commit()


def main():
    engine = create_engine("sqlite:///salmon.db", echo=False)
    Session = sessionmaker(bind=engine)
    Base = declarative_base()
    session = Session()
    mails = get_maybetestmails(session)
    delete_old_from_maybetestmail(mails)
    session.close()


if __name__ == "__main__":
    main()
