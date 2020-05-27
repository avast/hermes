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


confpath = os.path.dirname(os.path.realpath(__file__)) + "/../../../configuration/salmon.yaml"
with open(confpath) as f:
    data = yaml.load(f, Loader=yaml.FullLoader)

relay_config = {'host': data['relay']['relayhost'], 'port': data['relay']['relayport']}
receiver_config = {'maildir': data['directory']['queuepath']}
handlers = data['global']['handlers']
router_defaults = data['global']['router_defaults']

if data['relay']['mqtt']:
    client = iottl.Hermes(data['relay']['mqtt_server'], username=data['relay']['mqtt_username'], password=data['relay']['mqtt_password'])
    if not client.connect():
        logging.error('ERROR: Failed to connect to server!')
        sys.exit(1)

if data["relay"]["use_rule_file"]:
    with open(os.path.dirname(os.path.realpath(__file__)) + "/../../../configuration/rules.json") as json_file:
        rules = json.load(json_file)

if data["relay"]["analyze_text"]:
    nlp = spacy.load("en_core_web_sm")

# push username and password into database if it is not already there
for i in range(0, len(data['receiver']['credentials']), 2):
    username = data['receiver']['credentials'][i].strip('()')
    password = data['receiver']['credentials'][i+1].strip('()')
    if not are_credentials_in_db(username, password):
        credentials = Settings(username, password)
        push_into_db(credentials)
# the config/boot.py will turn these values into variables set in settings
