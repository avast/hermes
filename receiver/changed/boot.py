import logging.config

from salmon import queue
from salmon.routing import Router
from salmon.server import SMTPReceiver, Relay
import yaml
import os

from . import settings


logging.config.fileConfig("config/logging.conf")

with open(os.path.dirname(os.path.realpath(__file__)) + "/../../../configuration/salmon.yaml") as f:
    data = yaml.load(f, Loader=yaml.FullLoader)

# the relay host to actually send the final message to
settings.relay = Relay(host=data['relay']['relayhost'],
                       port=data['relay']['relayport'], debug=1)

# where to listen for incoming messages
settings.receiver = SMTPReceiver(data['receiver']['listenhost'],
                                 data['receiver']['listenport'])

Router.defaults(**data['global']['router_defaults'])
Router.load(data['global']['handlers'])
Router.RELOAD = True
Router.UNDELIVERABLE_QUEUE = queue.Queue("run/undeliverable")
