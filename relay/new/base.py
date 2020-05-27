"""base module.

This module creates the SQL connection.
Author: Silvie Chlupová
Date    Created: 03/31/2020
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging


if "PERMEABILITY_ENV" in os.environ:
    engine = create_engine("sqlite:///testing_salmon.db", echo=False)
elif "SALMON_SETTINGS_MODULE" in os.environ:
    engine = create_engine("sqlite:///:memory:", echo=False)
else:
    engine = create_engine("sqlite:///salmon.db", echo=False)

Session = sessionmaker(bind=engine)
Base = declarative_base()
logging.debug("[+] (base.py) - SQL connection created")
