import logging
import logging.config
import os
from salmon import queue
from salmon.routing import Router
from salmon.server import Relay, QueueReceiver

from . import settings

logging.config.fileConfig("config/logging.conf")

# the relay host to actually send the final message to
settings.relay = Relay(host=settings.relay_config['host'],
                       port=settings.relay_config['port'], debug=1)

# Include the maildir option we've set in settings.py
settings.receiver = QueueReceiver(settings.receiver_config['maildir'])

Router.defaults(**settings.router_defaults)
Router.load(settings.handlers)
Router.RELOAD = True
Router.UNDELIVERABLE_QUEUE = queue.Queue("run/undeliverable")
