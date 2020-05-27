
# This file contains python variables that configure Salmon for email processing.

# You may add additional parameters such as `username' and `password' if your
# relay server requires authentication, `starttls' (boolean) or `ssl' (boolean)
# for secure connections.
import yaml
import os

with open(os.path.dirname(os.path.realpath(__file__)) + "/../../../configuration/salmon.yaml") as f:
    data = yaml.load(f, Loader=yaml.FullLoader)

relay_config = {'host': data['relay']['relayhost'], 'port': data['relay']['relayport']}
receiver_config = {'host': data['receiver']['listenhost'], 'port': data['receiver']['listenport']}
handlers = data['global']['handlers']
router_defaults = data['global']['router_defaults']

# the config/boot.py will turn these values into variables set in settings
