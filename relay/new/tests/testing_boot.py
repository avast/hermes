import logging
import logging.config
import os
import sys
from salmon import queue
from salmon.routing import Router
from salmon.server import SMTPReceiver, Relay, QueueReceiver

if "PERMEABILITY_ENV" in os.environ:
    import testing_settings
else:
    from tests import testing_settings

logging.config.fileConfig("../config/test_logging_relay.conf")

testing_settings.relay = Relay(host=testing_settings.relay_config['host'],
                       port=testing_settings.relay_config['port'], debug=1)
testing_settings.receiver = QueueReceiver(testing_settings.receiver_config['maildir'])

Router.defaults(**testing_settings.router_defaults)
Router.load(testing_settings.handlers)
Router.RELOAD = True
Router.UNDELIVERABLE_QUEUE = queue.Queue("./undeliverable")
