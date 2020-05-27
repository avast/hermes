# This file contains python variables that configure Salmon for email processing.

# You may add additional parameters such as `username' and `password' if your
# relay server requires authentication, `starttls' (boolean) or `ssl' (boolean)
# for secure connections.
import os
import yaml
import iottl
import logging
import json
import spacy
import warnings
warnings.filterwarnings("ignore")
from salmon.salmonconclude import push_into_db
from salmon.salmondb import Settings
from salmon.salmondb import are_credentials_in_db


confpath = os.path.dirname(os.path.realpath(__file__)) + "/testing_salmon.yaml"
with open(confpath) as f:
    data = yaml.load(f, Loader=yaml.FullLoader)

relay_config = {'host': data['relay']['relayhost'], 'port': data['relay']['relayport']}
receiver_config = {'maildir': data['directory']['queuepath']}
handlers = data['global']['handlers']
router_defaults = data['global']['router_defaults']
